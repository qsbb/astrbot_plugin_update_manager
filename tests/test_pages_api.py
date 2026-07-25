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
        (f"/{module.PLUGIN_NAME}/rule", ("GET",)),
        (f"/{module.PLUGIN_NAME}/rule", ("POST",)),
        (f"/{module.PLUGIN_NAME}/catalog", ("GET",)),
        (f"/{module.PLUGIN_NAME}/catalog/enable", ("POST",)),
        (f"/{module.PLUGIN_NAME}/catalog/disable", ("POST",)),
        (f"/{module.PLUGIN_NAME}/recommendations", ("GET",)),
        (f"/{module.PLUGIN_NAME}/recommendations/check-latest", ("POST",)),
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


def test_apply_page_runtime_config_clears_optional_network_values(monkeypatch, tmp_path):
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
        return SimpleNamespace(
            version="1.0.0", loaded=True, activated=enabled
        )

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
        return SimpleNamespace(target_version="0.1.0")

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
    assert payload["self_update"] == {
        "current_version": module.__version__,
        "latest_version": "0.1.0",
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
    assert len(payload["items"]) == 5
    assert peak > 1
    assert force_values == [True] * 5
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


def test_recommendation_failure_payload_keeps_safe_registry_context(monkeypatch, tmp_path):
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
        item for item in payload["items"] if item["plugin_id"] == "astrbot_plugin_voice_hub"
    )
    assert voice["latest_version"] == "1.0.1"
    assert voice["update_available"] is True
    assert voice["version_status"] == "update_available"
    assert voice["actions"]["update"] is True


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
        return SimpleNamespace(version="0.6.2", loaded=True, activated=True)

    async def update(plugin_id, *, source_kind, source_url, archive_url=None):
        calls.append(("update", plugin_id, source_kind, source_url, archive_url))
        return SimpleNamespace(version="0.6.3", loaded=True, activated=True)

    async def get_plugin(plugin_id):
        return SimpleNamespace(version="0.6.2")

    async def latest(plugin_id, current_version, source_url, *, force_refresh=False):
        assert plugin_id == "astrbot_plugin_voice_hub"
        assert current_version == "0.6.2"
        assert force_refresh is True
        return SimpleNamespace(
            archive_url=(
                "https://api.github.com/repos/qsbb/"
                "astrbot_plugin_voice_hub/zipball/master"
            )
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
