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
        (f"/{module.PLUGIN_NAME}/catalog", ("GET",)),
        (f"/{module.PLUGIN_NAME}/recommendations", ("GET",)),
        (f"/{module.PLUGIN_NAME}/install", ("POST",)),
        (f"/{module.PLUGIN_NAME}/update", ("POST",)),
        (f"/{module.PLUGIN_NAME}/enable", ("POST",)),
        (f"/{module.PLUGIN_NAME}/disable", ("POST",)),
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
    assert plugin.registry.github_token == "secret"
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
        "name": "Demo",
        "version": "1.0.0",
        "activated": True,
        "loaded": True,
        "eligible": False,
        "reasons": ["SOURCE_UNKNOWN"],
        "source_kind": None,
        "source_url": None,
    }


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

    plugin.adapter.snapshot_plugins = snapshots
    capabilities = SimpleNamespace(
        install_plugin=True,
        update_plugin=True,
        turn_on_plugin=True,
        turn_off_plugin=True,
    )
    monkeypatch.setattr(plugin.adapter, "probe_capabilities", lambda: capabilities)
    payload = unwrap(asyncio.run(plugin._pages_recommendations()))
    assert [item["key"] for item in payload["items"]] == ["知", "言", "序", "声", "核"]
    assert all(
        item["repo_url"].startswith("https://github.com/qsbb/astrbot_plugin_")
        for item in payload["items"]
    )
    assert all(item["description_zh"] for item in payload["items"])
    assert payload["items"][0]["description_zh"] == (
        "主动学习对话知识，支持检索、验证与持续积累。"
    )
    core = payload["items"][-1]
    assert core["installed"] is True
    assert core["actions"]["update"] is False
    assert core["actions"]["disable"] is False


def test_recommendation_mutation_validates_trust_and_routes_adapter(monkeypatch, tmp_path):
    module = import_main(monkeypatch)
    plugin = module.UpdateManagerPlugin(context(tmp_path), {})
    calls = []

    async def request_voice_confirmed():
        return {"plugin_id": "astrbot_plugin_voice_hub", "confirm": True}

    async def request_voice_direct():
        return {"plugin_id": "astrbot_plugin_voice_hub"}

    async def install(plugin_id, *, repo_url):
        calls.append(("install", plugin_id, repo_url))
        return SimpleNamespace(version="0.6.2")

    async def enable(plugin_id, enabled):
        calls.append(("enabled", plugin_id, enabled))
        return SimpleNamespace(activated=enabled)

    monkeypatch.setattr(plugin, "_request_json", request_voice_confirmed)
    monkeypatch.setattr(plugin.adapter, "install_plugin", install)
    monkeypatch.setattr(plugin.adapter, "set_plugin_enabled", enable)
    assert unwrap(asyncio.run(plugin._pages_install()))["installed"] is True
    assert unwrap(asyncio.run(plugin._pages_disable()))["activated"] is False
    assert calls[0][2] == "https://github.com/qsbb/astrbot_plugin_voice_hub"

    monkeypatch.setattr(plugin, "_request_json", request_voice_direct)
    assert unwrap(asyncio.run(plugin._pages_enable()))["activated"] is True

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
            name="Demo",
            current_version="1.0.0",
            activated=True,
            loaded=True,
            eligible=False,
            reasons=("SOURCE_UNKNOWN",),
            source_kind=None,
            source_url=None,
        ),
    )
