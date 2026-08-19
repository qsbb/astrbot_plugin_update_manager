from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from types import SimpleNamespace

from test_plugin_entry import context, import_main


PLUGIN_ROOT = Path(__file__).resolve().parents[1]


def unwrap(response):
    return response[0] if isinstance(response, tuple) else response


def test_pages_routes_are_runtime_detected(monkeypatch, tmp_path):
    module = import_main(monkeypatch)
    routes = []
    ctx = context(tmp_path)
    ctx.register_web_api = lambda *args: routes.append(args)
    module.UpdateManagerPlugin(ctx, {})
    assert [(route[0], tuple(route[2])) for route in routes] == [
        (f"/{module.PLUGIN_NAME}/overview", ("GET",)),
        (f"/{module.PLUGIN_NAME}/config", ("GET",)),
        (f"/{module.PLUGIN_NAME}/config", ("POST",)),
        (f"/{module.PLUGIN_NAME}/mirrors", ("GET",)),
        (f"/{module.PLUGIN_NAME}/mirrors/benchmark", ("POST",)),
        (f"/{module.PLUGIN_NAME}/rule", ("GET",)),
        (f"/{module.PLUGIN_NAME}/rule", ("POST",)),
        (f"/{module.PLUGIN_NAME}/catalog", ("GET",)),
        (f"/{module.PLUGIN_NAME}/catalog/check-updates", ("POST",)),
        (f"/{module.PLUGIN_NAME}/catalog/update", ("POST",)),
        (f"/{module.PLUGIN_NAME}/catalog/enable", ("POST",)),
        (f"/{module.PLUGIN_NAME}/catalog/disable", ("POST",)),
        (f"/{module.PLUGIN_NAME}/diagnostics/logs", ("POST",)),
        (f"/{module.PLUGIN_NAME}/diagnostics/clear", ("POST",)),
        (f"/{module.PLUGIN_NAME}/recommendations", ("GET",)),
        (f"/{module.PLUGIN_NAME}/recommendations/check-latest", ("POST",)),
        (f"/{module.PLUGIN_NAME}/recommendations/apply-all", ("POST",)),
        (f"/{module.PLUGIN_NAME}/install", ("POST",)),
        (f"/{module.PLUGIN_NAME}/update", ("POST",)),
        (f"/{module.PLUGIN_NAME}/enable", ("POST",)),
        (f"/{module.PLUGIN_NAME}/disable", ("POST",)),
        (f"/{module.PLUGIN_NAME}/webui/admins", ("GET",)),
        (f"/{module.PLUGIN_NAME}/webui/admins/create", ("POST",)),
        (f"/{module.PLUGIN_NAME}/webui/admins/update", ("POST",)),
        (f"/{module.PLUGIN_NAME}/webui/url", ("GET",)),
        (f"/{module.PLUGIN_NAME}/webui/start", ("POST",)),
    ]


def test_pages_gracefully_skip_unsupported_runtime(monkeypatch, tmp_path):
    module = import_main(monkeypatch)
    plugin = module.UpdateManagerPlugin(context(tmp_path), {})
    assert plugin._register_pages_web_api() is False


def test_pages_config_never_returns_secret(monkeypatch, tmp_path):
    module = import_main(monkeypatch)
    plugin = module.UpdateManagerPlugin(
        context(tmp_path), {"github_token": "ghp-super-secret", "proxy": "http://proxy"}
    )
    payload = unwrap(asyncio.run(plugin._pages_get_config()))
    serialized = json.dumps(payload, ensure_ascii=False)
    assert "ghp-super-secret" not in serialized
    assert payload["config"]["github_token"] == {"configured": True}
    assert payload["schema"]["github_token"]["write_only"] is True
    assert payload["config"]["proxy"] == "http://proxy"


def test_apply_page_runtime_config_clears_optional_network_values(
    monkeypatch, tmp_path
):
    module = import_main(monkeypatch)
    plugin = module.UpdateManagerPlugin(
        context(tmp_path), {"proxy": "http://proxy", "github_token": "secret"}
    )
    plugin._config = {"proxy": None, "github_token": None}

    plugin._apply_page_runtime_config()

    assert plugin.registry.proxy is None
    assert plugin.registry.token is None


def test_pages_request_json_prefers_astrbot_web_contract(monkeypatch, tmp_path):
    module = import_main(monkeypatch)
    plugin = module.UpdateManagerPlugin(context(tmp_path), {})
    calls = []

    class Request:
        async def json(self, *, default):
            calls.append(default)
            return {"enabled": False}

        def get_json(self, **kwargs):
            raise AssertionError("AstrBot web request 不应走 Quart get_json")

    pages_api = sys.modules[plugin.__class__.__mro__[1].__module__]
    monkeypatch.setattr(pages_api, "request", Request())

    assert asyncio.run(plugin._request_json()) == {"enabled": False}
    assert calls == [{}]


def test_webui_modules_requires_session_and_filters_to_owned_contracts(
    monkeypatch, tmp_path
):
    module = import_main(monkeypatch)
    plugin = module.UpdateManagerPlugin(context(tmp_path), {})

    assert asyncio.run(plugin._pages_webui_modules())[1] == 401

    async def scan():
        return (
            SimpleNamespace(
                plugin_id="astrbot_plugin_update_manager",
                display_name="核",
                current_version="0.12.0",
                source_url="https://github.com/qsbb/astrbot_plugin_update_manager",
                activated=True,
                loaded=True,
                eligible=True,
            ),
            SimpleNamespace(
                plugin_id="astrbot_plugin_future_module",
                display_name="未来模块",
                current_version="1.0.0",
                source_url="https://github.com/qsbb/astrbot_plugin_future_module",
                activated=True,
                loaded=True,
                eligible=True,
            ),
            SimpleNamespace(
                plugin_id="astrbot_plugin_third_party",
                display_name="第三方",
                current_version="1.0.0",
                source_url="https://github.com/another/astrbot_plugin_third_party",
                activated=True,
                loaded=True,
                eligible=True,
            ),
        )

    class Provider:
        def diagnostic_log_contract(self):
            return {"name": "series.diagnostics", "version": "1.0"}

    async def get_instance(plugin_id):
        return Provider() if plugin_id != "astrbot_plugin_third_party" else None

    monkeypatch.setattr(plugin, "_webui_current_session", lambda: object())
    monkeypatch.setattr(plugin.catalog, "scan", scan)
    monkeypatch.setattr(plugin.adapter, "get_plugin_instance", get_instance)
    payload = unwrap(asyncio.run(plugin._pages_webui_modules()))
    assert {item["plugin_id"] for item in payload["modules"]} == {
        "astrbot_plugin_update_manager",
        "astrbot_plugin_future_module",
    }
    assert all(item["contracts"] == 1 for item in payload["modules"])
    assert all(item["contract_source"] == "self_declared" for item in payload["modules"])


def test_webui_url_uses_current_dashboard_host_for_wildcard_listener(
    monkeypatch, tmp_path
):
    module = import_main(monkeypatch)
    plugin = module.UpdateManagerPlugin(context(tmp_path), {})
    pages_api = sys.modules[plugin.__class__.__mro__[1].__module__]
    monkeypatch.setattr(
        pages_api, "request", SimpleNamespace(host="192.168.5.88:25520")
    )
    plugin.webui_server._started = True
    payload = unwrap(asyncio.run(plugin._pages_webui_url()))
    assert payload["enabled"] is True
    assert payload["ready"] is True
    assert payload["url"] == "http://192.168.5.88:25528"


def test_webui_start_enables_old_disabled_loopback_config(monkeypatch, tmp_path):
    module = import_main(monkeypatch)
    plugin = module.UpdateManagerPlugin(
        context(tmp_path), {"webui_enabled": False, "webui_host": "127.0.0.1"}
    )
    pages_api = sys.modules[plugin.__class__.__mro__[1].__module__]
    monkeypatch.setattr(
        pages_api, "request", SimpleNamespace(host="192.168.5.88:25520")
    )

    class StartedServer:
        host = "0.0.0.0"
        started = True

        @staticmethod
        def url_for_host(host=""):
            return f"http://{host}:25528"

    calls = []

    async def start(request_host):
        calls.append(request_host)
        return StartedServer()

    monkeypatch.setattr(plugin, "_start_webui_from_page", start)
    payload = unwrap(asyncio.run(plugin._pages_webui_start()))
    assert calls == ["192.168.5.88"]
    assert payload == {
        "success": True,
        "enabled": True,
        "ready": True,
        "url": "http://192.168.5.88:25528",
    }


def test_series_diagnostics_aggregate_isolated_contracts_and_redacts(
    monkeypatch, tmp_path
):
    module = import_main(monkeypatch)
    plugin = module.UpdateManagerPlugin(context(tmp_path), {})

    class Provider:
        def diagnostic_log_contract(self):
            return {"name": "series.diagnostics", "version": "1.0"}

        def diagnostic_events(self, *, after_seq, limit):
            assert after_seq == 3
            assert limit == 20
            return {
                "events": [
                    {
                        "seq": 4,
                        "timestamp": "2026-07-31T10:00:00+00:00",
                        "plugin_id": "untrusted",
                        "plugin_name": "伪造",
                        "level": "WARN",
                        "code": "tool.timeout",
                        "summary": (
                            "request 123456789 timed out "
                            "authorization=secret message='private text' "
                            "alice@example.com Abcdef1234567890Ghijkl"
                        ),
                        "details": {
                            "duration_ms": 6000,
                            "user_id": "123456789",
                            "log_detail": (
                                "tool call failed for user-a token abcdefghijk "
                                + "x" * 2500
                            ),
                        },
                    }
                ],
                "next_seq": 4,
                "dropped_before": 0,
            }

    provider = Provider()

    async def get_instance(plugin_id):
        if plugin_id == "astrbot_plugin_conversation_flow":
            return provider
        return None

    async def request_json():
        return {
            "cursors": {"astrbot_plugin_conversation_flow": 3},
            "limit": 20,
        }

    monkeypatch.setattr(plugin.adapter, "get_plugin_instance", get_instance)
    monkeypatch.setattr(plugin, "_request_json", request_json)
    payload = unwrap(asyncio.run(plugin._pages_diagnostic_logs()))
    event = next(
        item
        for item in payload["events"]
        if item["plugin_id"] == "astrbot_plugin_conversation_flow"
    )
    assert payload["contract"] == "series.diagnostics.aggregate@1.0"
    assert event["plugin_id"] == "astrbot_plugin_conversation_flow"
    assert event["plugin_name"] == "言"
    assert event["level"] == "WARNING"
    assert "123456789" not in event["summary"]
    assert "authorization=secret" not in event["summary"]
    assert "private text" not in event["summary"]
    assert "alice@example.com" not in event["summary"]
    assert "Abcdef1234567890Ghijkl" not in event["summary"]
    assert event["details"]["duration_ms"] == 6000
    detail = event["details"]["log_detail"]
    assert detail.startswith("tool call failed for <已隐藏标识> token=<已隐藏>")
    assert "user-a" not in detail
    assert "abcdefghijk" not in detail
    assert len(detail) == 2000
    member = next(item for item in payload["members"] if item["plugin_name"] == "言")
    assert member["status"] == "ready"
    assert member["next_seq"] == 4


def test_series_diagnostics_reads_legacy_embodiment_disabled_contract_without_blocking(
    monkeypatch, tmp_path
):
    module = import_main(monkeypatch)
    plugin = module.UpdateManagerPlugin(context(tmp_path), {})

    class LegacyEmbodimentProvider:
        def diagnostic_log_contract(self):
            return {
                "name": "series.diagnostics",
                "version": "1.0",
                "series_id": "ningxin_suxi",
                "plugin_id": "astrbot_plugin_quest_avatar_bridge",
                "plugin_name": "临",
                "capabilities": ("read_events", "clear_events"),
                "storage": "memory_only",
                "astrbot_log_propagation": False,
            }

        def diagnostic_events(self, *, after_seq, limit):
            assert after_seq == 0
            assert limit == 20
            return {
                "contract": "series.diagnostics@1.0",
                "plugin_id": "astrbot_plugin_quest_avatar_bridge",
                "plugin_name": "临",
                "status": "disabled",
                "reason": "DIAGNOSTIC_DISABLED",
                "stream_id": "legacy-embodiment-stream",
                "events": [],
                "next_seq": 0,
                "dropped_before": 0,
            }

        def diagnostic_clear(self):
            return None

    async def get_instance(plugin_id):
        if plugin_id == "astrbot_plugin_quest_avatar_bridge":
            return LegacyEmbodimentProvider()
        return None

    async def request_json():
        return {"cursors": {}, "limit": 20}

    async def snapshot_plugins():
        return (
            SimpleNamespace(
                name="astrbot_plugin_quest_avatar_bridge",
                root_dir_name="astrbot_plugin_quest_avatar_bridge",
                display_name="凝心溯溪-临",
                repo=("https://github.com/qsbb/astrbot_plugin_quest_avatar_bridge"),
                loaded=True,
            ),
        )

    monkeypatch.setattr(plugin.adapter, "get_plugin_instance", get_instance)
    monkeypatch.setattr(plugin.adapter, "snapshot_plugins", snapshot_plugins)
    monkeypatch.setattr(plugin, "_request_json", request_json)
    payload = unwrap(asyncio.run(plugin._pages_diagnostic_logs()))

    member = next(
        item
        for item in payload["members"]
        if item["plugin_id"] == "astrbot_plugin_embodiment_bridge"
    )
    assert member["plugin_name"] == "临"
    assert member["display_name"] == "凝心溯溪-临"
    assert member["status"] == "disabled"
    assert member["reason"] == "DIAGNOSTIC_DISABLED"
    assert not any(
        event["plugin_id"] == "astrbot_plugin_embodiment_bridge"
        for event in payload["events"]
    )


def test_series_diagnostics_rejects_untrusted_or_wrong_series_self_declarations(
    monkeypatch, tmp_path
):
    module = import_main(monkeypatch)
    plugin = module.UpdateManagerPlugin(context(tmp_path), {})

    class Provider:
        def __init__(self, plugin_id, series_id):
            self.plugin_id = plugin_id
            self.series_id = series_id

        def diagnostic_log_contract(self):
            return {
                "name": "series.diagnostics",
                "version": "1.0",
                "series_id": self.series_id,
                "plugin_id": self.plugin_id,
                "plugin_name": "新",
                "capabilities": ("read_events", "clear_events"),
                "storage": "memory_only",
                "astrbot_log_propagation": False,
            }

        def diagnostic_events(self, *, after_seq, limit):
            return {"events": [], "next_seq": 0, "dropped_before": 0}

        def diagnostic_clear(self):
            return None

    untrusted_id = "astrbot_plugin_untrusted_sample"
    wrong_series_id = "astrbot_plugin_wrong_series"
    providers = {
        untrusted_id: Provider(untrusted_id, "ningxin_suxi"),
        wrong_series_id: Provider(wrong_series_id, "another_series"),
    }

    async def get_instance(plugin_id):
        return providers.get(plugin_id)

    async def snapshot_plugins():
        return (
            SimpleNamespace(
                name=untrusted_id,
                root_dir_name=untrusted_id,
                display_name="不可信",
                repo=f"https://github.com/third-party/{untrusted_id}",
                loaded=True,
            ),
            SimpleNamespace(
                name=wrong_series_id,
                root_dir_name=wrong_series_id,
                display_name="错误系列",
                repo=f"https://github.com/qsbb/{wrong_series_id}",
                loaded=True,
            ),
        )

    async def request_json():
        return {"cursors": {}, "limit": 20}

    monkeypatch.setattr(plugin.adapter, "get_plugin_instance", get_instance)
    monkeypatch.setattr(plugin.adapter, "snapshot_plugins", snapshot_plugins)
    monkeypatch.setattr(plugin, "_request_json", request_json)

    payload = unwrap(asyncio.run(plugin._pages_diagnostic_logs()))
    member_ids = {item["plugin_id"] for item in payload["members"]}
    assert untrusted_id not in member_ids
    assert wrong_series_id not in member_ids


def test_series_diagnostics_clear_discovers_new_series_provider(monkeypatch, tmp_path):
    module = import_main(monkeypatch)
    plugin = module.UpdateManagerPlugin(context(tmp_path), {})
    plugin_id = "astrbot_plugin_future_series_feature"
    calls = []

    class Provider:
        def diagnostic_log_contract(self):
            return {
                "name": "series.diagnostics",
                "version": "1.0",
                "series_id": "ningxin_suxi",
                "plugin_id": plugin_id,
                "plugin_name": "新",
                "capabilities": ("read_events", "clear_events"),
                "storage": "memory_only",
                "astrbot_log_propagation": False,
            }

        def diagnostic_events(self, *, after_seq, limit):
            return {"events": [], "next_seq": 0, "dropped_before": 0}

        def diagnostic_clear(self):
            calls.append("cleared")

    provider = Provider()

    async def get_instance(requested_id):
        return provider if requested_id == plugin_id else None

    async def snapshot_plugins():
        return (
            SimpleNamespace(
                name=plugin_id,
                root_dir_name=plugin_id,
                display_name="凝心溯溪-新",
                repo=f"https://github.com/qsbb/{plugin_id}",
                loaded=True,
            ),
        )

    async def request_json():
        return {"confirm": True, "plugin_ids": [plugin_id]}

    monkeypatch.setattr(plugin.adapter, "get_plugin_instance", get_instance)
    monkeypatch.setattr(plugin.adapter, "snapshot_plugins", snapshot_plugins)
    monkeypatch.setattr(plugin, "_request_json", request_json)

    payload = unwrap(asyncio.run(plugin._pages_clear_diagnostic_logs()))
    assert payload["cleared"] == [plugin_id]
    assert payload["unavailable"] == []
    assert calls == ["cleared"]


def test_series_diagnostics_reads_astrbot_4_star_cls_without_adapter_stub(
    monkeypatch, tmp_path
):
    module = import_main(monkeypatch)

    class Provider:
        def diagnostic_log_contract(self):
            return {"name": "series.diagnostics", "version": "1.0"}

        def diagnostic_events(self, *, after_seq, limit):
            assert after_seq == 0
            assert limit == 20
            return {
                "events": [
                    {
                        "seq": 1,
                        "timestamp": "2026-07-31T10:00:00+00:00",
                        "level": "INFO",
                        "code": "plugin.ready",
                        "summary": "对话流插件初始化完成",
                        "details": {},
                    }
                ],
                "next_seq": 1,
                "dropped_before": 0,
                "stream_id": "conversation-flow-stream",
            }

    ctx = context(tmp_path)
    ctx.get_all_stars = lambda: [
        SimpleNamespace(
            name="astrbot_plugin_conversation_flow",
            root_dir_name="astrbot_plugin_conversation_flow",
            star_cls=Provider(),
        )
    ]
    plugin = module.UpdateManagerPlugin(ctx, {})

    async def request_json():
        return {"cursors": {}, "limit": 20}

    monkeypatch.setattr(plugin, "_request_json", request_json)
    payload = unwrap(asyncio.run(plugin._pages_diagnostic_logs()))
    member = next(
        item
        for item in payload["members"]
        if item["plugin_id"] == "astrbot_plugin_conversation_flow"
    )

    assert member["status"] == "ready"
    assert member["next_seq"] == 1
    event = next(
        item
        for item in payload["events"]
        if item["plugin_id"] == "astrbot_plugin_conversation_flow"
    )
    assert event["code"] == "plugin.ready"


def test_series_diagnostics_recovers_after_provider_sequence_reset(
    monkeypatch, tmp_path
):
    module = import_main(monkeypatch)
    plugin = module.UpdateManagerPlugin(context(tmp_path), {})
    calls = []

    class Provider:
        def diagnostic_log_contract(self):
            return {"name": "series.diagnostics", "version": "1.0"}

        def diagnostic_events(self, *, after_seq, limit):
            calls.append((after_seq, limit))
            return {
                "events": []
                if after_seq
                else [
                    {
                        "seq": 2,
                        "timestamp": "2026-07-31T10:00:00+00:00",
                        "level": "INFO",
                        "code": "plugin.ready",
                        "summary": "reloaded",
                    }
                ],
                "next_seq": 2,
                "dropped_before": 0,
            }

    async def get_instance(plugin_id):
        if plugin_id == "astrbot_plugin_conversation_flow":
            return Provider()
        return None

    from astrbot_plugin_update_manager.core.trusted import TRUSTED_SERIES

    item = next(
        candidate
        for candidate in TRUSTED_SERIES
        if candidate.plugin_id == "astrbot_plugin_conversation_flow"
    )
    monkeypatch.setattr(plugin.adapter, "get_plugin_instance", get_instance)
    member, events = asyncio.run(
        plugin._read_plugin_diagnostics(item, after_seq=10, limit=20)
    )

    assert calls == [(10, 20), (0, 20)]
    assert member["status"] == "ready"
    assert member["reset"] is True
    assert member["next_seq"] == 2
    assert [event["seq"] for event in events] == [2]


def test_series_diagnostics_resets_when_stream_changes_at_equal_cursor(
    monkeypatch, tmp_path
):
    module = import_main(monkeypatch)
    plugin = module.UpdateManagerPlugin(context(tmp_path), {})
    calls = []

    class Provider:
        def diagnostic_log_contract(self):
            return {"name": "series.diagnostics", "version": "1.0"}

        def diagnostic_events(self, *, after_seq, limit):
            calls.append((after_seq, limit))
            return {
                "stream_id": "new-stream",
                "events": []
                if after_seq
                else [
                    {
                        "seq": 2,
                        "timestamp": "2026-07-31T10:00:00+00:00",
                        "level": "INFO",
                        "code": "plugin.ready",
                        "summary": "reloaded",
                    }
                ],
                "next_seq": 2,
                "dropped_before": 0,
            }

    provider = Provider()

    async def get_instance(plugin_id):
        if plugin_id == "astrbot_plugin_conversation_flow":
            return provider
        return None

    from astrbot_plugin_update_manager.core.trusted import TRUSTED_SERIES

    item = next(
        candidate
        for candidate in TRUSTED_SERIES
        if candidate.plugin_id == "astrbot_plugin_conversation_flow"
    )
    monkeypatch.setattr(plugin.adapter, "get_plugin_instance", get_instance)
    member, events = asyncio.run(
        plugin._read_plugin_diagnostics(
            item,
            after_seq=2,
            limit=20,
            expected_stream_id="old-stream",
        )
    )

    assert calls == [(2, 20), (0, 20)]
    assert member["reset"] is True
    assert member["stream_id"] == "new-stream"
    assert [event["seq"] for event in events] == [2]


def test_series_diagnostics_times_out_one_provider_without_blocking_page(
    monkeypatch, tmp_path
):
    module = import_main(monkeypatch)
    plugin = module.UpdateManagerPlugin(context(tmp_path), {})
    pages_api = sys.modules[plugin.__class__.__mro__[1].__module__]
    monkeypatch.setattr(pages_api, "DIAGNOSTIC_READ_TIMEOUT_SECONDS", 0.01)

    class Provider:
        def diagnostic_log_contract(self):
            return {"name": "series.diagnostics", "version": "1.0"}

        async def diagnostic_events(self, *, after_seq, limit):
            await asyncio.sleep(0.05)
            return {"events": [], "next_seq": 0, "dropped_before": 0}

    async def get_instance(plugin_id):
        if plugin_id == "astrbot_plugin_conversation_flow":
            return Provider()
        return None

    from astrbot_plugin_update_manager.core.trusted import TRUSTED_SERIES

    item = next(
        candidate
        for candidate in TRUSTED_SERIES
        if candidate.plugin_id == "astrbot_plugin_conversation_flow"
    )
    monkeypatch.setattr(plugin.adapter, "get_plugin_instance", get_instance)
    member, events = asyncio.run(
        plugin._read_plugin_diagnostics(item, after_seq=0, limit=20)
    )

    assert member["status"] == "timeout"
    assert member["reason"] == "DIAGNOSTIC_READ_TIMEOUT"
    assert events == []


def test_series_diagnostics_reports_first_read_buffer_gap(monkeypatch, tmp_path):
    module = import_main(monkeypatch)
    plugin = module.UpdateManagerPlugin(context(tmp_path), {})

    class Provider:
        def diagnostic_log_contract(self):
            return {"name": "series.diagnostics", "version": "1.0"}

        def diagnostic_events(self, *, after_seq, limit):
            assert after_seq == 0
            assert limit == 1000
            return {
                "events": [],
                "next_seq": 305,
                "dropped_before": 5,
            }

    async def get_instance(plugin_id):
        if plugin_id == "astrbot_plugin_conversation_flow":
            return Provider()
        return None

    async def request_json():
        return {"cursors": {}, "limit": 1000}

    monkeypatch.setattr(plugin.adapter, "get_plugin_instance", get_instance)
    monkeypatch.setattr(plugin, "_request_json", request_json)
    payload = unwrap(asyncio.run(plugin._pages_diagnostic_logs()))
    member = next(
        item
        for item in payload["members"]
        if item["plugin_id"] == "astrbot_plugin_conversation_flow"
    )
    assert member["status"] == "ready"
    assert member["gap"] is True
    assert member["dropped_before"] == 5


def test_series_diagnostics_clear_validates_scope_and_degrades_missing(
    monkeypatch, tmp_path
):
    module = import_main(monkeypatch)
    plugin = module.UpdateManagerPlugin(context(tmp_path), {})
    calls = []

    class Provider:
        def diagnostic_clear(self):
            calls.append("cleared")

    async def get_instance(plugin_id):
        return Provider() if plugin_id == "astrbot_plugin_voice_hub" else None

    async def clear_without_confirmation():
        return {}

    monkeypatch.setattr(plugin.adapter, "get_plugin_instance", get_instance)
    monkeypatch.setattr(plugin, "_request_json", clear_without_confirmation)
    payload, status = asyncio.run(plugin._pages_clear_diagnostic_logs())
    assert status == 400
    assert payload["error"] == "CONFIRMATION_REQUIRED"
    assert calls == []

    async def clear_voice():
        return {"confirm": True, "plugin_ids": ["astrbot_plugin_voice_hub"]}

    monkeypatch.setattr(plugin, "_request_json", clear_voice)
    payload = unwrap(asyncio.run(plugin._pages_clear_diagnostic_logs()))
    assert payload["cleared"] == ["astrbot_plugin_voice_hub"]
    assert calls == ["cleared"]

    async def clear_untrusted():
        return {
            "confirm": True,
            "plugin_ids": ["astrbot_plugin_orchestration_hub"],
        }

    monkeypatch.setattr(plugin, "_request_json", clear_untrusted)
    payload, status = asyncio.run(plugin._pages_clear_diagnostic_logs())
    assert status == 403
    assert payload["error"] == "PLUGIN_NOT_TRUSTED"


def test_pages_save_config_validates_and_preserves_empty_token(monkeypatch, tmp_path):
    module = import_main(monkeypatch)
    plugin = module.UpdateManagerPlugin(
        context(tmp_path), {"github_token": "secret", "plan_ttl_seconds": 900}
    )

    async def valid_json():
        return {
            "enabled": False,
            "plan_ttl_seconds": 1200,
            "github_token": "",
            "log_level": "WARNING",
        }

    monkeypatch.setattr(plugin, "_request_json", valid_json)
    payload = unwrap(asyncio.run(plugin._pages_save_config()))
    assert payload["success"] is True
    assert plugin.enabled is False
    assert plugin.planner.ttl_seconds == 1200
    assert plugin.registry.token == "secret"
    persisted = plugin.store.read("manager-config.json", {})
    assert persisted["enabled"] is False
    assert "github_token" not in persisted

    async def invalid_json():
        return {"plugin_root": "C:/escape", "unknown": 1}

    monkeypatch.setattr(plugin, "_request_json", invalid_json)
    payload, status = asyncio.run(plugin._pages_save_config())
    assert status == 400
    assert payload["fields"] == {
        "plugin_root": "RESTART_ONLY_FIELD",
        "unknown": "UNKNOWN_FIELD",
    }


def test_pages_mirrors_lists_builtin_custom_and_selected(monkeypatch, tmp_path):
    module = import_main(monkeypatch)
    plugin = module.UpdateManagerPlugin(
        context(tmp_path),
        {
            "github_mirror": "https://hk.gh-proxy.com/",
            "github_mirror_candidates": "https://mine.example.com\nhttp://bad\nhttps://mine.example.com",
        },
    )
    payload = unwrap(asyncio.run(plugin._pages_mirrors()))
    assert payload["success"] is True
    assert payload["selected"] == "https://hk.gh-proxy.com"
    assert payload["direct"] is False
    # 自定义列表去重且丢弃非 https 项。
    assert payload["custom"] == ["https://mine.example.com"]
    urls = [item["url"] for item in payload["candidates"]]
    assert urls[:4] == [
        "https://edgeone.gh-proxy.com",
        "https://hk.gh-proxy.com",
        "https://gh-proxy.com",
        "https://gh.dpik.top",
    ]
    assert urls[-1] == "https://mine.example.com"
    assert [item["url"] for item in payload["candidates"] if item["selected"]] == [
        "https://hk.gh-proxy.com"
    ]
    assert all(item["builtin"] for item in payload["candidates"][:4])
    assert payload["probe_url"].startswith("https://raw.githubusercontent.com/")
    assert payload["benchmark_timeout_seconds"] == 5.0


def test_pages_mirrors_keeps_unknown_selection_visible(monkeypatch, tmp_path):
    module = import_main(monkeypatch)
    plugin = module.UpdateManagerPlugin(
        context(tmp_path), {"github_mirror": "https://legacy.example.com"}
    )
    payload = unwrap(asyncio.run(plugin._pages_mirrors()))
    selected = [item for item in payload["candidates"] if item["selected"]]
    assert [item["url"] for item in selected] == ["https://legacy.example.com"]
    assert selected[0]["builtin"] is False


def test_pages_benchmark_mirrors_reports_latency_without_raising(monkeypatch, tmp_path):
    module = import_main(monkeypatch)
    plugin = module.UpdateManagerPlugin(context(tmp_path), {})
    probes = []

    async def probe_latency(url, *, timeout_seconds):
        probes.append((url, timeout_seconds))
        if "gh-proxy.com" in url and url.startswith("https://gh-proxy.com/"):
            return False, None, "TIMEOUT"
        return True, 12.5, None

    monkeypatch.setattr(plugin.registry, "probe_latency", probe_latency)

    async def requested():
        return {
            "mirrors": ["https://gh-proxy.com", "https://hk.gh-proxy.com", "ftp://nope"]
        }

    monkeypatch.setattr(plugin, "_request_json", requested)
    payload = unwrap(asyncio.run(plugin._pages_benchmark_mirrors()))
    assert payload["success"] is True
    # 非法项在解析阶段被丢弃，不会出现在结果里。
    assert [item["url"] for item in payload["results"]] == [
        "https://gh-proxy.com",
        "https://hk.gh-proxy.com",
    ]
    assert payload["results"][0] == {
        "url": "https://gh-proxy.com",
        "available": False,
        "latency_ms": None,
        "error": "TIMEOUT",
    }
    assert payload["results"][1]["latency_ms"] == 12.5
    # 探针必须走镜像前缀，并复用配置的测速超时。
    assert probes[0][0] == (
        "https://gh-proxy.com/https://raw.githubusercontent.com/octocat/Hello-World/master/README"
    )
    assert {timeout for _, timeout in probes} == {5.0}
    assert payload["checked_at"]


def test_pages_benchmark_mirrors_defaults_to_all_candidates_and_rejects_bad_type(
    monkeypatch, tmp_path
):
    module = import_main(monkeypatch)
    plugin = module.UpdateManagerPlugin(
        context(tmp_path), {"github_mirror_candidates": "https://mine.example.com"}
    )

    async def probe_latency(url, *, timeout_seconds):
        return True, 1.0, None

    monkeypatch.setattr(plugin.registry, "probe_latency", probe_latency)

    async def empty_body():
        return {}

    monkeypatch.setattr(plugin, "_request_json", empty_body)
    payload = unwrap(asyncio.run(plugin._pages_benchmark_mirrors()))
    assert [item["url"] for item in payload["results"]] == [
        "https://edgeone.gh-proxy.com",
        "https://hk.gh-proxy.com",
        "https://gh-proxy.com",
        "https://gh.dpik.top",
        "https://mine.example.com",
    ]

    async def bad_type():
        return {"mirrors": "https://mine.example.com"}

    monkeypatch.setattr(plugin, "_request_json", bad_type)
    payload, status = asyncio.run(plugin._pages_benchmark_mirrors())
    assert status == 400
    assert payload["error"] == "INVALID_FIELD_TYPE:mirrors"


def test_pages_save_config_applies_mirror_and_rejects_insecure_prefix(
    monkeypatch, tmp_path
):
    module = import_main(monkeypatch)
    plugin = module.UpdateManagerPlugin(context(tmp_path), {})
    assert plugin.registry.mirror is None

    async def valid_mirror():
        return {"github_mirror": "https://gh.dpik.top/"}

    monkeypatch.setattr(plugin, "_request_json", valid_mirror)
    payload = unwrap(asyncio.run(plugin._pages_save_config()))
    assert payload["success"] is True
    # 热应用：保存后无需重启即刻生效，并已去掉尾斜杠。
    assert plugin.registry.mirror == "https://gh.dpik.top"
    assert payload["restart_required"] is False

    async def insecure_mirror():
        return {"github_mirror": "http://gh.dpik.top"}

    monkeypatch.setattr(plugin, "_request_json", insecure_mirror)
    payload, status = asyncio.run(plugin._pages_save_config())
    assert status == 400
    assert payload["fields"] == {"github_mirror": "INVALID_VALUE"}
    assert plugin.registry.mirror == "https://gh.dpik.top"

    async def clear_mirror():
        return {"github_mirror": ""}

    monkeypatch.setattr(plugin, "_request_json", clear_mirror)
    assert unwrap(asyncio.run(plugin._pages_save_config()))["success"] is True
    assert plugin.registry.mirror is None


def test_pages_save_config_rebuilds_or_removes_daily_schedule(monkeypatch, tmp_path):
    module = import_main(monkeypatch)
    plugin = module.UpdateManagerPlugin(context(tmp_path), {})
    calls = []

    async def rebuild():
        calls.append("rebuild")

    async def remove_job():
        calls.append("remove")

    monkeypatch.setattr(plugin.scheduler, "rebuild", rebuild)
    monkeypatch.setattr(plugin.scheduler, "remove_job", remove_job)

    async def enable_automatic():
        return {"enabled": True, "auto_update_enabled": True}

    monkeypatch.setattr(plugin, "_request_json", enable_automatic)
    payload = unwrap(asyncio.run(plugin._pages_save_config()))
    assert payload["success"] is True
    assert payload["schedule_updated"] is True
    assert calls == ["rebuild"]

    async def disable_plugin():
        return {"enabled": False}

    monkeypatch.setattr(plugin, "_request_json", disable_plugin)
    payload = unwrap(asyncio.run(plugin._pages_save_config()))
    assert payload["success"] is True
    assert payload["schedule_updated"] is True
    assert calls == ["rebuild", "remove"]


def test_pages_save_config_reports_persist_and_schedule_failures(monkeypatch, tmp_path):
    module = import_main(monkeypatch)
    plugin = module.UpdateManagerPlugin(context(tmp_path), {})

    async def disable_plugin():
        return {"enabled": False}

    monkeypatch.setattr(plugin, "_request_json", disable_plugin)

    def fail_write(name, value):
        raise OSError("disk full")

    monkeypatch.setattr(plugin.store, "write", fail_write)
    payload, status = asyncio.run(plugin._pages_save_config())
    assert status == 500
    assert payload == {
        "success": False,
        "error": "CONFIG_PERSIST_FAILED",
        "detail": "disk full",
    }
    assert plugin.enabled is True
    assert plugin._config_overrides == {}

    plugin = module.UpdateManagerPlugin(context(tmp_path / "schedule"), {})

    async def enable_automatic():
        return {"enabled": True, "auto_update_enabled": True}

    async def fail_rebuild():
        raise RuntimeError("cron backend unavailable")

    monkeypatch.setattr(plugin, "_request_json", enable_automatic)
    monkeypatch.setattr(plugin.scheduler, "rebuild", fail_rebuild)
    payload, status = asyncio.run(plugin._pages_save_config())
    assert status == 500
    assert payload["success"] is False
    assert payload["error"] == "SCHEDULE_UPDATE_FAILED"
    assert payload["detail"] == "cron backend unavailable"
    assert payload["persisted"]["local"] is True


def test_overview_capabilities_keep_code_and_bilingual_metadata(monkeypatch, tmp_path):
    module = import_main(monkeypatch)
    plugin = module.UpdateManagerPlugin(context(tmp_path), {})
    payload = unwrap(asyncio.run(plugin._pages_overview()))
    capabilities = payload["runtime"]["capabilities"]
    assert [item["code"] for item in capabilities] == [
        "plugin_manager",
        "list_plugins",
        "install_sources",
        "install_plugin",
        "update_plugin",
        "turn_on_plugin",
        "turn_off_plugin",
        "reload_plugin",
        "cron",
    ]
    assert all(set(item["label"]) == {"zh-CN", "en-US"} for item in capabilities)
    assert all(set(item["comment"]) == {"zh-CN", "en-US"} for item in capabilities)


def _rule_item(plugin_id="demo", *, eligible=True, loaded=True):
    return SimpleNamespace(
        plugin_id=plugin_id,
        name="Demo",
        display_name="Demo",
        current_version="1.0.0",
        eligible=eligible,
        loaded=loaded,
    )


def test_rule_page_get_and_post_preserve_fields_and_rebuild(monkeypatch, tmp_path):
    module = import_main(monkeypatch)
    plugin = module.UpdateManagerPlugin(
        context(tmp_path), {"enabled": True, "auto_update_enabled": True}
    )
    plugin.catalog.scan = lambda: asyncio.sleep(0, result=(_rule_item(),))
    initial = unwrap(asyncio.run(plugin._pages_get_rule()))
    assert initial["catalog"] == [
        {"plugin_id": "demo", "display_name": "Demo", "version": "1.0.0"}
    ]
    assert initial["rule"]["policy"] == "check_only"
    assert initial["policy_note"] == "CHECK_ONLY_WILL_NOT_UPDATE"
    calls = []

    async def request_rule():
        return {
            "expected_revision": 0,
            "enabled": True,
            "plugin_ids": ["demo"],
            "local_time": "05:15",
        }

    async def rebuild():
        calls.append("rebuild")

    monkeypatch.setattr(plugin, "_request_json", request_rule)
    monkeypatch.setattr(plugin.scheduler, "rebuild", rebuild)
    payload = unwrap(asyncio.run(plugin._pages_save_rule()))
    assert payload["rule"]["revision"] == 1
    assert payload["rule"]["local_time"] == "05:15"
    assert payload["rule"]["timezone"] == "Asia/Shanghai"
    assert payload["rule"]["jitter_minutes"] == 10
    assert payload["schedule_action"] == "rebuilt"
    assert calls == ["rebuild"]


def test_rule_page_strict_whitelist_cas_catalog_and_global_gate(monkeypatch, tmp_path):
    module = import_main(monkeypatch)
    plugin = module.UpdateManagerPlugin(context(tmp_path), {})
    plugin.catalog.scan = lambda: asyncio.sleep(
        0, result=(_rule_item(), _rule_item("blocked", eligible=False))
    )

    async def unknown():
        return {"expected_revision": 0, "surprise": True}

    monkeypatch.setattr(plugin, "_request_json", unknown)
    payload, status = asyncio.run(plugin._pages_save_rule())
    assert status == 400 and payload["error"] == "UNKNOWN_RULE_FIELDS"

    async def blocked():
        return {"expected_revision": 0, "plugin_ids": ["blocked"]}

    monkeypatch.setattr(plugin, "_request_json", blocked)
    payload, status = asyncio.run(plugin._pages_save_rule())
    assert status == 400
    assert payload["error"] == "PLUGIN_NOT_CURRENTLY_ELIGIBLE_OR_LOADED"

    async def self_target():
        return {"expected_revision": 0, "plugin_ids": [module.PLUGIN_NAME]}

    monkeypatch.setattr(plugin, "_request_json", self_target)
    payload, status = asyncio.run(plugin._pages_save_rule())
    assert status == 400 and payload["error"] == "SELF_RULE_TARGET_BLOCKED"

    calls = []

    async def disabled_rule():
        return {"expected_revision": 0, "plugin_ids": ["demo"]}

    async def remove():
        calls.append("remove")

    monkeypatch.setattr(plugin, "_request_json", disabled_rule)
    monkeypatch.setattr(plugin.scheduler, "remove_job", remove)
    payload = unwrap(asyncio.run(plugin._pages_save_rule()))
    assert payload["schedule_action"] == "removed"
    assert calls == ["remove"]

    async def stale():
        return {"expected_revision": 0, "local_time": "06:00"}

    monkeypatch.setattr(plugin, "_request_json", stale)
    payload, status = asyncio.run(plugin._pages_save_rule())
    assert status == 409 and payload["error"] == "RULE_REVISION_CONFLICT"
    assert payload["current_revision"] == 1


def test_pages_catalog_payload(monkeypatch, tmp_path):
    module = import_main(monkeypatch)
    plugin = module.UpdateManagerPlugin(context(tmp_path), {})
    plugin.catalog.scan = lambda: _catalog_result()
    plugin.adapter.last_discovery_report = SimpleNamespace(
        runtime_count=1, discovered_count=0, roots_checked=1, diagnostics=()
    )
    payload = unwrap(asyncio.run(plugin._pages_catalog()))
    assert payload["success"] is True
    assert payload["diagnostics"]["runtime_count"] == 1
    assert payload["items"][0] == {
        "plugin_id": "demo",
        "display_name": "Demo",
        "version": "1.0.0",
        "activated": True,
        "loaded": True,
        "eligible": False,
        "reasons": ["SOURCE_UNKNOWN"],
        "source_kind": None,
        "source_url": None,
        "lifecycle": {
            "operable": False,
            "reason": "LIFECYCLE_CAPABILITY_UNAVAILABLE",
        },
        "update_lifecycle": {
            "checkable": False,
            "operable": False,
            "reason": "SOURCE_REQUIRED",
        },
    }


def test_catalog_lifecycle_api_accepts_loaded_nontrusted_and_verifies_snapshot(
    monkeypatch, tmp_path
):
    module = import_main(monkeypatch)
    plugin = module.UpdateManagerPlugin(context(tmp_path), {})
    item = _rule_item("third_party")
    item.activated = False
    item.reasons = ()
    plugin.catalog.scan = lambda: asyncio.sleep(0, result=(item,))
    monkeypatch.setattr(
        plugin.adapter,
        "probe_capabilities",
        lambda: SimpleNamespace(turn_on_plugin=True, turn_off_plugin=True),
    )
    calls = []

    async def request_enable():
        return {"plugin_id": "third_party"}

    async def set_enabled(plugin_id, enabled):
        calls.append((plugin_id, enabled))
        return SimpleNamespace(version="1.0.0", loaded=True, activated=enabled)

    monkeypatch.setattr(plugin, "_request_json", request_enable)
    monkeypatch.setattr(plugin.adapter, "set_plugin_enabled", set_enabled)
    payload = unwrap(asyncio.run(plugin._pages_catalog_enable()))
    assert payload["success"] is True
    assert payload["activated"] is True
    assert payload["lifecycle"]["snapshot_verified"] is True
    assert calls == [("third_party", True)]

    async def request_disable():
        return {"plugin_id": "third_party", "confirm": True}

    item.activated = True
    monkeypatch.setattr(plugin, "_request_json", request_disable)
    payload = unwrap(asyncio.run(plugin._pages_catalog_disable()))
    assert payload["activated"] is False
    assert calls[-1] == ("third_party", False)


def test_catalog_lifecycle_blocks_missing_confirmation_self_and_unloaded(
    monkeypatch, tmp_path
):
    module = import_main(monkeypatch)
    plugin = module.UpdateManagerPlugin(context(tmp_path), {})
    monkeypatch.setattr(
        plugin.adapter,
        "probe_capabilities",
        lambda: SimpleNamespace(turn_on_plugin=True, turn_off_plugin=True),
    )
    loaded = _rule_item("third_party")
    loaded.activated = True
    loaded.reasons = ()
    unloaded = _rule_item("unloaded", loaded=False)
    unloaded.activated = False
    unloaded.reasons = ("PLUGIN_NOT_LOADED",)
    plugin.catalog.scan = lambda: asyncio.sleep(0, result=(loaded, unloaded))

    async def no_confirmation():
        return {"plugin_id": "third_party"}

    monkeypatch.setattr(plugin, "_request_json", no_confirmation)
    payload, status = asyncio.run(plugin._pages_catalog_disable())
    assert status == 400 and payload["error"] == "CONFIRMATION_REQUIRED"

    async def self_request():
        return {"plugin_id": module.PLUGIN_NAME}

    monkeypatch.setattr(plugin, "_request_json", self_request)
    payload, status = asyncio.run(plugin._pages_catalog_enable())
    assert status == 403 and payload["error"] == "SELF_LIFECYCLE_BLOCKED"

    async def unloaded_request():
        return {"plugin_id": "unloaded"}

    monkeypatch.setattr(plugin, "_request_json", unloaded_request)
    payload, status = asyncio.run(plugin._pages_catalog_enable())
    assert status == 409 and payload["error"] == "PLUGIN_NOT_LOADED"


def _github_catalog_item(
    plugin_id="third_party",
    *,
    version="1.0.0",
    source_kind="github",
    source_url="https://github.com/owner/third_party",
):
    return SimpleNamespace(
        plugin_id=plugin_id,
        name="Third Party",
        display_name="Third Party",
        current_version=version,
        activated=True,
        loaded=True,
        eligible=True,
        reasons=(),
        source_kind=source_kind,
        source_url=source_url,
    )


def test_catalog_check_updates_is_scoped_and_isolates_single_failures(
    monkeypatch, tmp_path
):
    """目录检查只探测有 GitHub 来源的行，且单个仓库失败不能拖垮整批。

    market 来源与缺 URL 的行在进网络调用前就该被挡掉，否则等于拿必然失败的
    请求去消耗 GitHub 匿名配额。
    """
    module = import_main(monkeypatch)
    plugin = module.UpdateManagerPlugin(context(tmp_path), {})
    good = _github_catalog_item("good")
    broken = _github_catalog_item("broken")
    market = _github_catalog_item("market", source_kind="market", source_url=None)
    plugin.catalog.scan = lambda: asyncio.sleep(0, result=(good, broken, market))
    monkeypatch.setattr(
        plugin.adapter,
        "probe_capabilities",
        lambda: SimpleNamespace(
            turn_on_plugin=True, turn_off_plugin=True, update_plugin=True
        ),
    )

    async def latest(plugin_id, current_version, source_url, *, force_refresh=False):
        assert force_refresh is True
        if plugin_id == "broken":
            raise RuntimeError("REGISTRY_HTTP_404")
        return SimpleNamespace(target_version="1.1.0", archive_url="https://zip")

    async def payload():
        return {}

    monkeypatch.setattr(plugin, "_request_json", payload)
    monkeypatch.setattr(plugin.registry, "github_latest", latest)
    result = unwrap(asyncio.run(plugin._pages_check_catalog()))
    assert result["success"] is True
    by_id = {item["plugin_id"]: item for item in result["items"]}
    assert set(by_id) == {"good", "broken"}
    assert by_id["good"]["update_available"] is True
    assert by_id["good"]["latest_version"] == "1.1.0"
    assert by_id["broken"]["version_status"] == "check_failed"
    assert by_id["broken"]["update_available"] is False
    assert by_id["broken"]["error"]

    async def scoped():
        return {"plugin_ids": ["good"]}

    monkeypatch.setattr(plugin, "_request_json", scoped)
    scoped_result = unwrap(asyncio.run(plugin._pages_check_catalog()))
    assert [item["plugin_id"] for item in scoped_result["items"]] == ["good"]

    async def bad_flag():
        return {"force_refresh": "yes"}

    monkeypatch.setattr(plugin, "_request_json", bad_flag)
    payload_error, status = asyncio.run(plugin._pages_check_catalog())
    assert status == 400
    assert payload_error["error"] == "INVALID_FIELD_TYPE:force_refresh"


def test_catalog_update_requires_confirmation_source_and_new_version(
    monkeypatch, tmp_path
):
    """目录更新的四条底线：二次确认、GitHub 来源、有新版本、禁止自更新。"""
    module = import_main(monkeypatch)
    plugin = module.UpdateManagerPlugin(context(tmp_path), {})
    target = _github_catalog_item("third_party")
    market = _github_catalog_item("market", source_kind="market", source_url=None)
    myself = _github_catalog_item(module.PLUGIN_NAME)
    plugin.catalog.scan = lambda: asyncio.sleep(0, result=(target, market, myself))
    monkeypatch.setattr(
        plugin.adapter,
        "probe_capabilities",
        lambda: SimpleNamespace(
            turn_on_plugin=True, turn_off_plugin=True, update_plugin=True
        ),
    )
    calls = []
    remote_version = "1.1.0"

    async def latest(plugin_id, current_version, source_url, *, force_refresh=False):
        assert force_refresh is True
        return SimpleNamespace(target_version=remote_version, archive_url="https://zip")

    async def update(plugin_id, *, source_kind, source_url, archive_url=None):
        calls.append((plugin_id, source_kind, source_url, archive_url))
        return SimpleNamespace(version=remote_version, loaded=True, activated=True)

    monkeypatch.setattr(plugin.registry, "github_latest", latest)
    monkeypatch.setattr(plugin.adapter, "update_plugin", update)

    async def confirmed():
        return {"plugin_id": "third_party", "confirm": True}

    monkeypatch.setattr(plugin, "_request_json", confirmed)
    payload = unwrap(asyncio.run(plugin._pages_catalog_update()))
    assert payload["success"] is True and payload["updated"] is True
    assert payload["version"] == "1.1.0"
    assert calls == [
        (
            "third_party",
            "github",
            "https://github.com/owner/third_party",
            "https://zip",
        )
    ]

    async def unconfirmed():
        return {"plugin_id": "third_party"}

    monkeypatch.setattr(plugin, "_request_json", unconfirmed)
    error, status = asyncio.run(plugin._pages_catalog_update())
    assert status == 400 and error["error"] == "CONFIRMATION_REQUIRED"

    async def market_request():
        return {"plugin_id": "market", "confirm": True}

    monkeypatch.setattr(plugin, "_request_json", market_request)
    error, status = asyncio.run(plugin._pages_catalog_update())
    assert status == 409 and error["error"] == "SOURCE_REQUIRED"

    async def self_request():
        return {"plugin_id": module.PLUGIN_NAME, "confirm": True}

    monkeypatch.setattr(plugin, "_request_json", self_request)
    error, status = asyncio.run(plugin._pages_catalog_update())
    assert status == 403 and error["error"] == "SELF_UPDATE_BLOCKED"

    # 远端与本地同版本时必须在下载与热重载之前就拒绝。
    remote_version = "1.0.0"
    monkeypatch.setattr(plugin, "_request_json", confirmed)
    error, status = asyncio.run(plugin._pages_catalog_update())
    assert status == 409 and error["error"] == "NO_UPDATE_AVAILABLE"
    assert len(calls) == 1


def test_catalog_force_update_allows_supported_version_states_only(
    monkeypatch, tmp_path
):
    module = import_main(monkeypatch)
    plugin = module.UpdateManagerPlugin(context(tmp_path), {})
    target = _github_catalog_item("third_party")
    plugin.catalog.scan = lambda: asyncio.sleep(0, result=(target,))
    monkeypatch.setattr(
        plugin.adapter,
        "probe_capabilities",
        lambda: SimpleNamespace(
            turn_on_plugin=True, turn_off_plugin=True, update_plugin=True
        ),
    )
    remote_version = "1.0.0"
    calls = []

    async def latest(plugin_id, current_version, source_url, *, force_refresh=False):
        return SimpleNamespace(
            target_version=remote_version,
            archive_url="https://api.github.com/repos/owner/third_party/zipball/main",
        )

    async def update(plugin_id, *, source_kind, source_url, archive_url=None):
        calls.append((plugin_id, source_kind, source_url, archive_url))
        return SimpleNamespace(version=remote_version, loaded=True, activated=True)

    monkeypatch.setattr(plugin.registry, "github_latest", latest)
    monkeypatch.setattr(plugin.adapter, "update_plugin", update)

    async def force_request():
        return {"plugin_id": "third_party", "confirm": True, "force": True}

    monkeypatch.setattr(plugin, "_request_json", force_request)
    same = unwrap(asyncio.run(plugin._pages_catalog_update()))
    assert same["forced"] is True
    assert same["version_status"] == "up_to_date"

    remote_version = "0.9.0"
    older = unwrap(asyncio.run(plugin._pages_catalog_update()))
    assert older["forced"] is True
    assert older["version_status"] == "local_newer"

    remote_version = "1.1.0"
    newer = unwrap(asyncio.run(plugin._pages_catalog_update()))
    assert newer["forced"] is True
    assert newer["version_status"] == "update_available"
    assert len(calls) == 3

    remote_version = "not-a-version"
    error, status = asyncio.run(plugin._pages_catalog_update())
    assert status == 409
    assert error["error"] == "FORCE_UPDATE_VERSION_UNAVAILABLE"
    assert len(calls) == 3


def test_catalog_force_update_keeps_confirmation_and_safety_gates(
    monkeypatch, tmp_path
):
    module = import_main(monkeypatch)
    plugin = module.UpdateManagerPlugin(context(tmp_path), {})
    target = _github_catalog_item("third_party")
    market = _github_catalog_item("market", source_kind="market", source_url=None)
    myself = _github_catalog_item(module.PLUGIN_NAME)
    plugin.catalog.scan = lambda: asyncio.sleep(0, result=(target, market, myself))
    capabilities = SimpleNamespace(
        turn_on_plugin=True, turn_off_plugin=True, update_plugin=True
    )
    monkeypatch.setattr(plugin.adapter, "probe_capabilities", lambda: capabilities)

    payloads = (
        ({"plugin_id": "third_party", "force": True}, "CONFIRMATION_REQUIRED", 400),
        (
            {"plugin_id": "third_party", "confirm": True, "force": "yes"},
            "INVALID_FORCE_FLAG",
            400,
        ),
        (
            {"plugin_id": "market", "confirm": True, "force": True},
            "SOURCE_REQUIRED",
            409,
        ),
        (
            {"plugin_id": module.PLUGIN_NAME, "confirm": True, "force": True},
            "SELF_UPDATE_BLOCKED",
            403,
        ),
    )
    for payload, code, expected_status in payloads:

        async def request(payload=payload):
            return payload

        monkeypatch.setattr(plugin, "_request_json", request)
        error, status = asyncio.run(plugin._pages_catalog_update())
        assert status == expected_status
        assert error["error"] == code

    capabilities.update_plugin = False

    async def no_capability():
        return {"plugin_id": "third_party", "confirm": True, "force": True}

    monkeypatch.setattr(plugin, "_request_json", no_capability)
    error, status = asyncio.run(plugin._pages_catalog_update())
    assert status == 503
    assert error["error"] == "UPDATE_CAPABILITY_UNAVAILABLE"


def test_pages_catalog_reports_empty_discovery_diagnostics(monkeypatch, tmp_path):
    module = import_main(monkeypatch)
    plugin = module.UpdateManagerPlugin(context(tmp_path), {})

    async def empty_catalog():
        return ()

    plugin.catalog.scan = empty_catalog
    plugin.adapter.last_discovery_report = SimpleNamespace(
        runtime_count=0,
        discovered_count=0,
        roots_checked=0,
        diagnostics=("DISCOVERY_ROOT_UNAVAILABLE",),
    )
    payload = unwrap(asyncio.run(plugin._pages_catalog()))
    assert payload["items"] == []
    assert payload["diagnostics"]["messages"] == [
        "DISCOVERY_ROOT_UNAVAILABLE",
        "DISCOVERY_UNAVAILABLE",
    ]


def test_recommendations_are_fixed_and_self_actions_are_blocked(monkeypatch, tmp_path):
    module = import_main(monkeypatch)
    plugin = module.UpdateManagerPlugin(context(tmp_path), {})

    async def snapshots():
        return (
            SimpleNamespace(
                name=module.PLUGIN_NAME,
                root_dir_name=module.PLUGIN_NAME,
                version=module.__version__,
                loaded=True,
                activated=True,
            ),
        )

    async def latest(plugin_id, current_version, source_url, *, force_refresh=False):
        # 远端版本跟随本地版本，断言的是"已是最新"这一语义；
        # 写死字面量会在每次发布 bump 后误报 local_newer。
        return SimpleNamespace(target_version=module.__version__)

    plugin.adapter.snapshot_plugins = snapshots
    monkeypatch.setattr(plugin.registry, "github_latest", latest)
    capabilities = SimpleNamespace(
        install_plugin=True,
        update_plugin=True,
        turn_on_plugin=True,
        turn_off_plugin=True,
    )
    monkeypatch.setattr(plugin.adapter, "probe_capabilities", lambda: capabilities)
    payload = unwrap(asyncio.run(plugin._pages_recommendations()))
    assert [item["key"] for item in payload["items"]] == [
        "知",
        "言",
        "序",
        "情",
        "境",
        "声",
        "临",
        "核",
    ]
    assert all(
        item["repo_url"].startswith("https://github.com/qsbb/astrbot_plugin_")
        for item in payload["items"]
    )
    relationship = next(
        item
        for item in payload["items"]
        if item["plugin_id"] == "astrbot_plugin_relationship"
    )
    assert relationship["name"] == "凝心溯溪-情"
    assert (
        relationship["repo_url"]
        == "https://github.com/qsbb/astrbot_plugin_relationship"
    )
    environment = next(
        item
        for item in payload["items"]
        if item["plugin_id"] == "astrbot_plugin_environment_awareness"
    )
    assert environment["name"] == "凝心溯溪-境"
    assert environment["repo_url"] == (
        "https://github.com/qsbb/astrbot_plugin_environment_awareness"
    )
    assert environment["description_zh"] == (
        "按需感知当地日历、天气、空气质量、官方预警和相关自然事件；免 API Key。"
    )
    assert all(item["description_zh"] for item in payload["items"])
    assert payload["items"][0]["description_zh"] == (
        "主动学习对话知识，支持检索、验证与持续积累。"
    )
    core = payload["items"][-1]
    assert core["installed"] is True
    assert core["actions"]["update"] is False
    assert core["actions"]["disable"] is False
    assert payload["self_update"] == {
        "current_version": module.__version__,
        "latest_version": module.__version__,
        "update_available": False,
        "version_status": "up_to_date",
        "checked_at": core["checked_at"],
        "error": None,
        "repo_url": "https://github.com/qsbb/astrbot_plugin_update_manager",
    }
    assert all(
        {"latest_version", "update_available", "version_status", "checked_at", "error"}
        <= item.keys()
        for item in payload["items"]
    )


def test_self_update_check_reports_repository_update_without_self_action(
    monkeypatch, tmp_path
):
    module = import_main(monkeypatch)
    plugin = module.UpdateManagerPlugin(context(tmp_path), {})

    async def snapshots():
        return (
            SimpleNamespace(
                name=module.PLUGIN_NAME,
                root_dir_name="凝心溯溪-核",
                version="0.1.0",
                loaded=True,
                activated=True,
            ),
        )

    async def latest(plugin_id, current_version, source_url, *, force_refresh=False):
        target = "0.2.0" if plugin_id == module.PLUGIN_NAME else "0.1.0"
        return SimpleNamespace(target_version=target)

    plugin.adapter.snapshot_plugins = snapshots
    monkeypatch.setattr(plugin.registry, "github_latest", latest)
    monkeypatch.setattr(
        plugin.adapter,
        "probe_capabilities",
        lambda: SimpleNamespace(
            install_plugin=True,
            update_plugin=True,
            turn_on_plugin=True,
            turn_off_plugin=True,
        ),
    )
    payload = unwrap(asyncio.run(plugin._pages_recommendations()))
    core = next(
        item for item in payload["items"] if item["plugin_id"] == module.PLUGIN_NAME
    )
    assert payload["self_update"]["update_available"] is True
    assert payload["self_update"]["latest_version"] == "0.2.0"
    assert payload["self_update"]["repo_url"] == core["repo_url"]
    assert core["actions"]["update"] is False


def test_legacy_embodiment_install_uses_canonical_recommendation_and_updates_by_alias(
    monkeypatch, tmp_path
):
    module = import_main(monkeypatch)
    plugin = module.UpdateManagerPlugin(context(tmp_path), {})
    canonical_id = "astrbot_plugin_embodiment_bridge"
    legacy_id = "astrbot_plugin_quest_avatar_bridge"
    canonical_repo = f"https://github.com/qsbb/{canonical_id}"
    legacy_snapshot = SimpleNamespace(
        name=legacy_id,
        root_dir_name=legacy_id,
        version="1.0.0",
        loaded=True,
        activated=True,
    )
    update_calls = []

    async def snapshots():
        return (legacy_snapshot,)

    async def get_plugin(plugin_id):
        return legacy_snapshot if plugin_id == legacy_id else None

    async def latest(plugin_id, current_version, source_url, *, force_refresh=False):
        if plugin_id == canonical_id:
            assert current_version == "1.0.0"
            assert source_url == canonical_repo
            return SimpleNamespace(target_version="1.1.0", archive_url="https://example.invalid/archive")
        return SimpleNamespace(target_version="1.0.0", archive_url="")

    async def update(plugin_id, *, source_kind, source_url, archive_url=None):
        update_calls.append((plugin_id, source_kind, source_url, archive_url))
        return SimpleNamespace(version="1.1.0", loaded=True, activated=True)

    async def request_legacy_update():
        return {"plugin_id": legacy_id, "confirm": True}

    plugin.adapter.snapshot_plugins = snapshots
    monkeypatch.setattr(plugin.adapter, "get_plugin", get_plugin)
    monkeypatch.setattr(plugin.adapter, "update_plugin", update)
    monkeypatch.setattr(plugin.registry, "github_latest", latest)
    monkeypatch.setattr(
        plugin.adapter,
        "probe_capabilities",
        lambda: SimpleNamespace(
            install_plugin=True,
            update_plugin=True,
            turn_on_plugin=True,
            turn_off_plugin=True,
        ),
    )

    payload = unwrap(asyncio.run(plugin._pages_recommendations()))
    item = next(entry for entry in payload["items"] if entry["plugin_id"] == canonical_id)
    assert item["installed"] is True
    assert item["repo_url"] == canonical_repo
    assert item["actions"]["update"] is True

    monkeypatch.setattr(plugin, "_request_json", request_legacy_update)
    updated = unwrap(asyncio.run(plugin._pages_update()))
    assert updated["plugin_id"] == canonical_id
    assert update_calls == [
        (legacy_id, "github", canonical_repo, "https://example.invalid/archive")
    ]


def test_canonical_embodiment_install_wins_over_legacy_duplicate(monkeypatch, tmp_path):
    module = import_main(monkeypatch)
    plugin = module.UpdateManagerPlugin(context(tmp_path), {})
    canonical_id = "astrbot_plugin_embodiment_bridge"
    legacy_id = "astrbot_plugin_quest_avatar_bridge"
    canonical_snapshot = SimpleNamespace(
        name=canonical_id,
        root_dir_name=canonical_id,
        version="1.0.0",
        loaded=True,
        activated=True,
    )
    legacy_snapshot = SimpleNamespace(
        name=legacy_id,
        root_dir_name=legacy_id,
        version="0.4.23",
        loaded=False,
        activated=False,
    )

    async def snapshots():
        return (legacy_snapshot, canonical_snapshot)

    async def latest(plugin_id, current_version, source_url, *, force_refresh=False):
        assert plugin_id == canonical_id
        assert current_version == "1.0.0"
        return SimpleNamespace(target_version="1.0.0", archive_url="")

    plugin.adapter.snapshot_plugins = snapshots
    monkeypatch.setattr(plugin.registry, "github_latest", latest)

    payload = unwrap(asyncio.run(plugin._pages_recommendations()))
    items = [item for item in payload["items"] if item["plugin_id"] == canonical_id]
    assert len(items) == 1
    assert items[0]["installed"] is True
    assert items[0]["version"] == "1.0.0"
    assert items[0]["loaded"] is True
    assert items[0]["activated"] is True


def test_recommendation_latest_check_is_parallel_forced_and_failure_isolated(
    monkeypatch, tmp_path
):
    module = import_main(monkeypatch)
    plugin = module.UpdateManagerPlugin(context(tmp_path), {})
    active = 0
    peak = 0
    force_values = []

    async def latest(plugin_id, current_version, source_url, *, force_refresh=False):
        nonlocal active, peak
        force_values.append(force_refresh)
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0.01)
        active -= 1
        if plugin_id == "astrbot_plugin_identity_guardian":
            raise RuntimeError("RATE_LIMITED")
        return SimpleNamespace(target_version="9.9.9")

    monkeypatch.setattr(plugin.registry, "github_latest", latest)
    payload = unwrap(asyncio.run(plugin._pages_check_recommendations()))
    assert payload["success"] is True
    assert len(payload["items"]) == 8
    assert peak > 1
    assert force_values == [True] * 8
    failed = next(
        item
        for item in payload["items"]
        if item["plugin_id"] == "astrbot_plugin_identity_guardian"
    )
    assert failed["version_status"] == "check_failed"
    assert failed["error"] == "RATE_LIMITED"
    assert failed["error_detail"] == "RATE_LIMITED"
    assert failed["error_context"] == {"repo": failed["repo_url"]}
    assert all(item["checked_at"] for item in payload["items"])


def test_check_latest_honours_cached_request_and_rejects_bad_flag(
    monkeypatch, tmp_path
):
    module = import_main(monkeypatch)
    plugin = module.UpdateManagerPlugin(context(tmp_path), {})
    force_values = []

    async def latest(plugin_id, current_version, source_url, *, force_refresh=False):
        force_values.append(force_refresh)
        return SimpleNamespace(target_version="9.9.9")

    monkeypatch.setattr(plugin.registry, "github_latest", latest)

    # 页面自动检查显式请求缓存，不得强制刷新以免触发限流。
    async def cached_payload():
        return {"force_refresh": False}

    monkeypatch.setattr(plugin, "_request_json", cached_payload)
    payload = unwrap(asyncio.run(plugin._pages_check_recommendations()))
    assert payload["success"] is True
    assert force_values == [False] * 8

    # 缺省仍是手动强制刷新语义。
    force_values.clear()

    async def empty_payload():
        return {}

    monkeypatch.setattr(plugin, "_request_json", empty_payload)
    assert unwrap(asyncio.run(plugin._pages_check_recommendations()))["success"] is True
    assert force_values == [True] * 8

    # 非布尔值必须拒绝，不能被静默当成真值。
    force_values.clear()

    async def invalid_payload():
        return {"force_refresh": "false"}

    monkeypatch.setattr(plugin, "_request_json", invalid_payload)
    response = asyncio.run(plugin._pages_check_recommendations())
    body, status = response if isinstance(response, tuple) else (response, 200)
    assert status == 400
    assert body["success"] is False
    assert body["error"] == "INVALID_FIELD_TYPE:force_refresh"
    assert force_values == []


def test_version_state_compares_across_v_prefix_and_segment_formats(
    monkeypatch, tmp_path
):
    """页面版本状态判断必须吃下 v 前缀与四段式，禁止字符串比较。

    系列插件即将统一为三段式无 v 前缀（如声 v0.7.4 → 0.7.5），过渡期本地
    metadata 里仍可能是旧格式；packaging.Version 原生接受最多一个前导 v，
    这里钉住跨格式升级判定与同值判定。
    """
    module = import_main(monkeypatch)
    plugin = module.UpdateManagerPlugin(context(tmp_path), {})
    # v 前缀 → 三段式的补丁升级必须判定为有新版本。
    assert plugin._version_state("v0.7.4", "0.7.5") == (True, "update_available")
    # 同版本跨格式不得误报升级。
    assert plugin._version_state("v0.7.5", "0.7.5") == (False, "up_to_date")
    # 四段式与三段式按数值等价与比较（知 1.2.0.0 → 1.2.0 / 1.2.1）。
    assert plugin._version_state("1.2.0.0", "1.2.0") == (False, "up_to_date")
    assert plugin._version_state("1.2.0.0", "1.2.1") == (True, "update_available")
    # 数值比较而非字符串比较：0.7.10 > 0.7.9。
    assert plugin._version_state("0.7.9", "0.7.10") == (True, "update_available")
    assert plugin._version_state("0.7.10", "0.7.9") == (False, "local_newer")
    # 本地比远端新（远端还是旧 v 前缀）不得误报升级。
    assert plugin._version_state("0.7.5", "v0.7.4") == (False, "local_newer")
    # 非法版本与未安装维持既有语义。
    assert plugin._version_state("vv1.0", "1.0.0") == (False, "unknown")
    assert plugin._version_state("", "1.0.0") == (False, "not_installed")


def test_recommendation_failure_payload_keeps_safe_registry_context(
    monkeypatch, tmp_path
):
    module = import_main(monkeypatch)
    plugin = module.UpdateManagerPlugin(context(tmp_path), {})
    pages_api = sys.modules[plugin.__class__.__mro__[1].__module__]

    async def latest(plugin_id, current_version, source_url, *, force_refresh=False):
        raise pages_api.RegistryError(
            "REGISTRY_HTTP_403",
            http_status=403,
            repo="qsbb/example",
            default_branch="main",
        )

    monkeypatch.setattr(plugin.registry, "github_latest", latest)
    payload = unwrap(asyncio.run(plugin._pages_check_recommendations()))
    failed = payload["items"][0]
    assert failed["error"] == "REGISTRY_HTTP_403"
    assert failed["error_detail"] == "REGISTRY_HTTP_403"
    assert failed["error_context"] == {
        "repo": "qsbb/example",
        "default_branch": "main",
        "http_status": 403,
    }


def test_recommendation_rate_limit_failure_exposes_retry_and_token_hint(
    monkeypatch, tmp_path
):
    module = import_main(monkeypatch)
    plugin = module.UpdateManagerPlugin(context(tmp_path), {})
    pages_api = sys.modules[plugin.__class__.__mro__[1].__module__]

    async def latest(plugin_id, current_version, source_url, *, force_refresh=False):
        raise pages_api.RegistryError(
            "REGISTRY_RATE_LIMITED",
            http_status=403,
            repo="qsbb/example",
            rate_limited=True,
            retry_after_seconds=420,
            reset_at="2024-05-01T00:00:00+00:00",
            token_configured=False,
        )

    monkeypatch.setattr(plugin.registry, "github_latest", latest)
    payload = unwrap(asyncio.run(plugin._pages_check_recommendations()))
    failed = payload["items"][0]
    assert failed["error"] == "REGISTRY_RATE_LIMITED"
    assert failed["error_context"]["rate_limited"] is True
    assert failed["error_context"]["retry_after_seconds"] == 420
    assert failed["error_context"]["reset_at"] == "2024-05-01T00:00:00+00:00"
    # 未配置 token 时必须提示可通过配置 token 提升额度。
    assert failed["error_context"]["token_hint_required"] is True
    assert failed["error_context"]["token_configured"] is False


def test_recommendation_rate_limit_hint_suppressed_when_token_configured(
    monkeypatch, tmp_path
):
    module = import_main(monkeypatch)
    plugin = module.UpdateManagerPlugin(context(tmp_path), {"github_token": "ghp_x"})
    pages_api = sys.modules[plugin.__class__.__mro__[1].__module__]

    async def latest(plugin_id, current_version, source_url, *, force_refresh=False):
        raise pages_api.RegistryError(
            "REGISTRY_RATE_LIMITED",
            repo="qsbb/example",
            rate_limited=True,
            retry_after_seconds=60,
            token_configured=True,
        )

    monkeypatch.setattr(plugin.registry, "github_latest", latest)
    payload = unwrap(asyncio.run(plugin._pages_check_recommendations()))
    context_payload = payload["items"][0]["error_context"]
    assert context_payload["token_configured"] is True
    assert context_payload["token_hint_required"] is False


def test_recommendations_payload_reports_global_rate_limit_snapshot(
    monkeypatch, tmp_path
):
    module = import_main(monkeypatch)
    plugin = module.UpdateManagerPlugin(context(tmp_path), {})

    async def latest(plugin_id, current_version, source_url, *, force_refresh=False):
        return SimpleNamespace(target_version="9.9.9")

    monkeypatch.setattr(plugin.registry, "github_latest", latest)
    monkeypatch.setattr(
        plugin.registry,
        "rate_limit_status",
        lambda: {
            "limited": True,
            "retry_after_seconds": 300,
            "reset_at": "2024-05-01T00:00:00+00:00",
            "remaining": 0,
            "limit": 60,
            "token_configured": False,
        },
    )
    payload = unwrap(asyncio.run(plugin._pages_recommendations()))
    assert payload["rate_limit"]["limited"] is True
    assert payload["rate_limit"]["retry_after_seconds"] == 300
    assert payload["rate_limit"]["remaining"] == 0
    assert "token" not in json.dumps(payload["rate_limit"]).replace(
        "token_configured", ""
    )


def test_recommendation_failure_detail_redacts_tokens(monkeypatch, tmp_path):
    module = import_main(monkeypatch)
    plugin = module.UpdateManagerPlugin(context(tmp_path), {})

    async def latest(plugin_id, current_version, source_url, *, force_refresh=False):
        raise RuntimeError("request failed with Bearer ghp_super_secret")

    monkeypatch.setattr(plugin.registry, "github_latest", latest)
    payload = unwrap(asyncio.run(plugin._pages_check_recommendations()))
    serialized = json.dumps(payload, ensure_ascii=False)
    failed = payload["items"][0]
    assert failed["error"] == "RUNTIMEERROR"
    assert failed["error_detail"] == "request failed with ***"
    assert "ghp_super_secret" not in serialized


def test_update_action_requires_newer_version(monkeypatch, tmp_path):
    module = import_main(monkeypatch)
    plugin = module.UpdateManagerPlugin(context(tmp_path), {})

    async def snapshots():
        return (
            SimpleNamespace(
                name="astrbot_plugin_voice_hub",
                root_dir_name="astrbot_plugin_voice_hub",
                version="1.0.0",
                loaded=True,
                activated=True,
            ),
        )

    async def latest(plugin_id, current_version, source_url, *, force_refresh=False):
        target = "1.0.1" if plugin_id == "astrbot_plugin_voice_hub" else "1.0.0"
        return SimpleNamespace(target_version=target)

    plugin.adapter.snapshot_plugins = snapshots
    monkeypatch.setattr(plugin.registry, "github_latest", latest)
    capabilities = SimpleNamespace(
        install_plugin=True,
        update_plugin=True,
        turn_on_plugin=True,
        turn_off_plugin=True,
    )
    monkeypatch.setattr(plugin.adapter, "probe_capabilities", lambda: capabilities)
    payload = unwrap(asyncio.run(plugin._pages_recommendations()))
    voice = next(
        item
        for item in payload["items"]
        if item["plugin_id"] == "astrbot_plugin_voice_hub"
    )
    assert voice["latest_version"] == "1.0.1"
    assert voice["update_available"] is True
    assert voice["version_status"] == "update_available"
    assert voice["actions"]["update"] is True
    assert voice["actions"]["force_update"] is True
    self_item = next(
        item for item in payload["items"] if item["plugin_id"] == module.PLUGIN_NAME
    )
    assert self_item["actions"]["force_update"] is False


def test_recommendation_mutation_validates_trust_and_routes_adapter(
    monkeypatch, tmp_path
):
    module = import_main(monkeypatch)
    plugin = module.UpdateManagerPlugin(context(tmp_path), {})
    calls = []

    async def request_voice_confirmed():
        return {"plugin_id": "astrbot_plugin_voice_hub", "confirm": True}

    async def request_voice_direct():
        return {"plugin_id": "astrbot_plugin_voice_hub"}

    async def install(plugin_id, *, repo_url):
        calls.append(("install", plugin_id, repo_url))
        return SimpleNamespace(version="0.6.2", loaded=True, activated=True)

    async def update(plugin_id, *, source_kind, source_url, archive_url=None):
        calls.append(("update", plugin_id, source_kind, source_url, archive_url))
        return SimpleNamespace(version="0.6.3", loaded=True, activated=True)

    async def get_plugin(plugin_id):
        return SimpleNamespace(version="0.6.2", loaded=True)

    async def latest(plugin_id, current_version, source_url, *, force_refresh=False):
        assert plugin_id == "astrbot_plugin_voice_hub"
        assert current_version == "0.6.2"
        assert force_refresh is True
        return SimpleNamespace(
            target_version="0.6.3",
            archive_url=(
                "https://api.github.com/repos/qsbb/"
                "astrbot_plugin_voice_hub/zipball/master"
            ),
        )

    async def enable(plugin_id, enabled):
        calls.append(("enabled", plugin_id, enabled))
        return SimpleNamespace(version="0.6.2", loaded=True, activated=enabled)

    monkeypatch.setattr(plugin, "_request_json", request_voice_confirmed)
    monkeypatch.setattr(plugin.adapter, "install_plugin", install)
    monkeypatch.setattr(plugin.adapter, "get_plugin", get_plugin)
    monkeypatch.setattr(plugin.adapter, "update_plugin", update)
    monkeypatch.setattr(plugin.adapter, "set_plugin_enabled", enable)
    monkeypatch.setattr(plugin.registry, "github_latest", latest)
    installed = unwrap(asyncio.run(plugin._pages_install()))
    assert installed["installed"] is True
    assert installed["lifecycle"]["snapshot_verified"] is True
    assert installed["lifecycle"]["direct_load"] is True
    assert installed["lifecycle"]["internal_hot_reload"] is False
    assert installed["lifecycle"]["extra_reload"] is False
    assert installed["lifecycle"]["extra_reload_performed"] is False
    updated = unwrap(asyncio.run(plugin._pages_update()))
    assert updated["lifecycle"]["direct_load"] is False
    assert updated["lifecycle"]["internal_hot_reload"] is True
    assert updated["lifecycle"]["extra_reload"] is False
    assert calls[1] == (
        "update",
        "astrbot_plugin_voice_hub",
        "github",
        "https://github.com/qsbb/astrbot_plugin_voice_hub",
        "https://api.github.com/repos/qsbb/astrbot_plugin_voice_hub/zipball/master",
    )
    disabled = unwrap(asyncio.run(plugin._pages_disable()))
    assert disabled["activated"] is False
    assert disabled["lifecycle"]["snapshot"]["activated"] is False
    assert disabled["lifecycle"]["internal_hot_reload"] is False
    assert calls[0][2] == "https://github.com/qsbb/astrbot_plugin_voice_hub"

    monkeypatch.setattr(plugin, "_request_json", request_voice_direct)
    enabled = unwrap(asyncio.run(plugin._pages_enable()))
    assert enabled["activated"] is True
    assert enabled["lifecycle"]["internal_hot_reload"] is True
    assert enabled["lifecycle"]["extra_reload"] is False

    async def request_untrusted():
        return {"plugin_id": "evil", "confirm": True}

    monkeypatch.setattr(plugin, "_request_json", request_untrusted)
    payload, status = asyncio.run(plugin._pages_install())
    assert status == 403
    assert payload["error"] == "PLUGIN_NOT_TRUSTED"

    async def request_self():
        return {"plugin_id": module.PLUGIN_NAME, "confirm": True}

    monkeypatch.setattr(plugin, "_request_json", request_self)
    assert asyncio.run(plugin._pages_update())[1] == 403
    assert asyncio.run(plugin._pages_disable())[1] == 403


def test_recommendation_force_update_allows_only_checked_version_states(
    monkeypatch, tmp_path
):
    module = import_main(monkeypatch)
    plugin = module.UpdateManagerPlugin(context(tmp_path), {})
    plugin_id = "astrbot_plugin_environment_awareness"
    remote_version = "1.0.0"
    calls = []

    async def force_request():
        return {"plugin_id": plugin_id, "confirm": True, "force": True}

    async def get_plugin(requested_plugin_id):
        assert requested_plugin_id == plugin_id
        return SimpleNamespace(version="1.0.0", loaded=True)

    async def latest(
        requested_plugin_id, current_version, source_url, *, force_refresh=False
    ):
        assert requested_plugin_id == plugin_id
        assert current_version == "1.0.0"
        assert source_url == (
            "https://github.com/qsbb/astrbot_plugin_environment_awareness"
        )
        assert force_refresh is True
        return SimpleNamespace(target_version=remote_version, archive_url="https://zip")

    async def update(requested_plugin_id, *, source_kind, source_url, archive_url=None):
        calls.append((requested_plugin_id, source_kind, source_url, archive_url))
        return SimpleNamespace(version=remote_version, loaded=True, activated=True)

    monkeypatch.setattr(plugin, "_request_json", force_request)
    monkeypatch.setattr(plugin.adapter, "get_plugin", get_plugin)
    monkeypatch.setattr(plugin.adapter, "update_plugin", update)
    monkeypatch.setattr(plugin.registry, "github_latest", latest)

    same = unwrap(asyncio.run(plugin._pages_update()))
    assert same["forced"] is True
    assert same["version_status"] == "up_to_date"

    remote_version = "0.9.0"
    older = unwrap(asyncio.run(plugin._pages_update()))
    assert older["forced"] is True
    assert older["version_status"] == "local_newer"

    remote_version = "1.1.0"
    newer = unwrap(asyncio.run(plugin._pages_update()))
    assert newer["forced"] is True
    assert newer["version_status"] == "update_available"
    assert len(calls) == 3

    remote_version = "not-a-version"
    error, status = asyncio.run(plugin._pages_update())
    assert status == 409
    assert error["error"] == "FORCE_UPDATE_VERSION_UNAVAILABLE"
    assert len(calls) == 3


def test_recommendation_update_validates_force_and_keeps_normal_version_gate(
    monkeypatch, tmp_path
):
    module = import_main(monkeypatch)
    plugin = module.UpdateManagerPlugin(context(tmp_path), {})
    plugin_id = "astrbot_plugin_voice_hub"
    calls = []

    async def get_plugin(_plugin_id):
        return SimpleNamespace(version="1.0.0", loaded=True)

    async def latest(*_args, **_kwargs):
        return SimpleNamespace(target_version="1.0.0", archive_url="https://zip")

    async def update(*_args, **_kwargs):
        calls.append("update")
        return SimpleNamespace(version="1.0.0", loaded=True, activated=True)

    monkeypatch.setattr(plugin.adapter, "get_plugin", get_plugin)
    monkeypatch.setattr(plugin.adapter, "update_plugin", update)
    monkeypatch.setattr(plugin.registry, "github_latest", latest)

    cases = (
        (
            {"plugin_id": plugin_id, "confirm": True, "force": "yes"},
            "INVALID_FORCE_FLAG",
            400,
        ),
        (
            {"plugin_id": module.PLUGIN_NAME, "confirm": True, "force": True},
            "SELF_UPDATE_BLOCKED",
            403,
        ),
        (
            {"plugin_id": "evil", "confirm": True, "force": True},
            "PLUGIN_NOT_TRUSTED",
            403,
        ),
    )
    for request_payload, code, expected_status in cases:

        async def request(request_payload=request_payload):
            return request_payload

        monkeypatch.setattr(plugin, "_request_json", request)
        error, status = asyncio.run(plugin._pages_update())
        assert status == expected_status
        assert error["error"] == code

    async def normal_request():
        return {"plugin_id": plugin_id, "confirm": True}

    monkeypatch.setattr(plugin, "_request_json", normal_request)
    error, status = asyncio.run(plugin._pages_update())
    assert status == 409
    assert error["error"] == "NO_UPDATE_AVAILABLE"
    assert calls == []


def test_apply_all_recommendations_runs_serially_and_reports_partial_failure(
    monkeypatch, tmp_path
):
    module = import_main(monkeypatch)
    plugin = module.UpdateManagerPlugin(context(tmp_path), {})
    calls = []

    async def confirmed():
        return {"confirm": True}

    async def recommendations(*, force_refresh):
        assert force_refresh is True
        return {
            "items": [
                {
                    "plugin_id": "astrbot_plugin_knowledge_base",
                    "actions": {"install": True, "update": False},
                },
                {
                    "plugin_id": "astrbot_plugin_voice_hub",
                    "actions": {"install": False, "update": True},
                },
                {
                    "plugin_id": module.PLUGIN_NAME,
                    "actions": {"install": False, "update": False},
                },
            ]
        }

    async def apply(plugin_id, operation):
        calls.append((plugin_id, operation))
        if operation == "update":
            raise RuntimeError("boom")
        return {
            "plugin_id": plugin_id,
            "operation": operation,
            "success": True,
            "version": "1.0.0",
            "lifecycle": {},
        }

    monkeypatch.setattr(plugin, "_request_json", confirmed)
    monkeypatch.setattr(plugin, "_recommendation_payload", recommendations)
    monkeypatch.setattr(plugin, "_apply_recommended_plugin", apply)
    payload = unwrap(asyncio.run(plugin._pages_apply_all_recommendations()))

    assert calls == [
        ("astrbot_plugin_knowledge_base", "install"),
        ("astrbot_plugin_voice_hub", "update"),
    ]
    assert payload["success"] is True
    assert payload["all_succeeded"] is False
    assert payload["total"] == 2
    assert payload["succeeded"] == 1
    assert payload["failed"] == 1
    assert payload["results"][1]["error"] == "RUNTIMEERROR"


def test_apply_all_recommendations_requires_explicit_confirmation(
    monkeypatch, tmp_path
):
    module = import_main(monkeypatch)
    plugin = module.UpdateManagerPlugin(context(tmp_path), {})

    for payload in (
        {},
        {"confirm": False},
        {"confirm": 1},
        {"confirm": True, "extra": 1},
    ):

        async def request(payload=payload):
            return payload

        monkeypatch.setattr(plugin, "_request_json", request)
        response, status = asyncio.run(plugin._pages_apply_all_recommendations())
        assert status == 400
        assert response["error"] == "CONFIRMATION_REQUIRED"


def test_destructive_recommendation_mutations_require_explicit_confirmation(
    monkeypatch, tmp_path
):
    module = import_main(monkeypatch)
    plugin = module.UpdateManagerPlugin(context(tmp_path), {})

    for payload in (
        {"plugin_id": "astrbot_plugin_voice_hub"},
        {"plugin_id": "astrbot_plugin_voice_hub", "confirm": False},
        {"plugin_id": "astrbot_plugin_voice_hub", "confirm": 1},
    ):

        async def request(payload=payload):
            return payload

        monkeypatch.setattr(plugin, "_request_json", request)
        handlers = (plugin._pages_install, plugin._pages_update, plugin._pages_disable)
        for handler in handlers:
            response, status = asyncio.run(handler())
            assert status == 400
            assert response["error"] == "CONFIRMATION_REQUIRED"


async def _catalog_result():
    return (
        SimpleNamespace(
            plugin_id="demo",
            display_name="Demo",
            current_version="1.0.0",
            activated=True,
            loaded=True,
            eligible=False,
            reasons=("SOURCE_UNKNOWN",),
            source_kind=None,
            source_url=None,
        ),
    )
