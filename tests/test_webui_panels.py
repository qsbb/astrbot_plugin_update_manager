"""series.webui@1.0 面板契约网关与 WebUI 生命周期路由测试。"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

import aiohttp

sys.path.insert(0, str(Path(__file__).resolve().parents[1].parent))

from astrbot_plugin_update_manager.core.trusted import (  # noqa: E402
    DIAGNOSTIC_SERIES_ID,
)
from astrbot_plugin_update_manager.core.webui_auth import WebUIAuth  # noqa: E402
from astrbot_plugin_update_manager.core.webui_panels import (  # noqa: E402
    WebUIPanelsGateway,
)
from astrbot_plugin_update_manager.core.webui_server import WebUIServer  # noqa: E402
from astrbot_plugin_update_manager.core.adapters.storage import AtomicJsonStore  # noqa: E402

PLUGIN_ID = "astrbot_plugin_relationship"


class FakePanelPlugin:
    """实现 series.webui@1.0 契约的桩插件。"""

    def __init__(self, fail_action: bool = False) -> None:
        self.fail_action = fail_action
        self.calls: list[tuple] = []

    def webui_panels_contract(self):
        return {
            "name": "series.webui@1.0",
            "plugin_id": PLUGIN_ID,
            "series_id": DIAGNOSTIC_SERIES_ID,
            "panels": [
                {"id": "overview", "title": "关系总览", "description": "全部关系状态"}
            ],
        }

    async def webui_panel_data(self, panel):
        self.calls.append(("data", panel))
        return {
            "success": True,
            "title": "关系总览",
            "columns": [{"key": "user", "label": "用户"}, {"key": "score", "label": "好感"}],
            "rows": [{"user": "1483904397", "score": 88}],
            "actions": [
                {
                    "id": "set_type",
                    "label": "设置关系性质",
                    "confirm": "确认设置？",
                    "payload_fields": [
                        {"name": "relationship_type", "type": "select", "options": [["lover", "情侣"]]}
                    ],
                }
            ],
        }

    async def webui_panel_action(self, panel, action, payload):
        self.calls.append(("action", panel, action, payload))
        if self.fail_action:
            raise RuntimeError("boom")
        return {"success": True, "message": "已设置", "applied": payload}


class FakeAdapter:
    def __init__(self, instance) -> None:
        self.instance = instance

    async def get_plugin_instance(self, plugin_id):
        return self.instance if plugin_id == PLUGIN_ID else None


def test_panels_gateway_happy_path():
    plugin = FakePanelPlugin()
    gateway = WebUIPanelsGateway(FakeAdapter(plugin))

    listing = asyncio.run(gateway.panels(PLUGIN_ID))
    assert listing["plugin_id"] == PLUGIN_ID
    assert listing["panels"][0]["id"] == "overview"

    data = asyncio.run(gateway.data(PLUGIN_ID, "overview"))
    assert data["success"] is True
    assert data["rows"][0]["user"] == "1483904397"

    result = asyncio.run(
        gateway.action(PLUGIN_ID, "overview", "set_type", {"relationship_type": "lover"}, "owner")
    )
    assert result["applied"] == {"relationship_type": "lover"}


def test_panels_gateway_rejects_untrusted_plugin():
    gateway = WebUIPanelsGateway(FakeAdapter(FakePanelPlugin()))
    try:
        asyncio.run(gateway.panels("some_random_plugin"))
    except LookupError as exc:
        assert "PLUGIN_NOT_TRUSTED" in str(exc)
    else:
        raise AssertionError("untrusted plugin must be rejected")


def test_panels_gateway_rejects_wrong_contract():
    class WrongContract(FakePanelPlugin):
        def webui_panels_contract(self):
            return {"name": "other.contract", "plugin_id": PLUGIN_ID}

    gateway = WebUIPanelsGateway(FakeAdapter(WrongContract()))
    try:
        asyncio.run(gateway.panels(PLUGIN_ID))
    except LookupError as exc:
        assert "CONTRACT" in str(exc)
    else:
        raise AssertionError("wrong contract must be rejected")


def test_panels_gateway_requires_admin_for_actions():
    gateway = WebUIPanelsGateway(FakeAdapter(FakePanelPlugin()))
    try:
        asyncio.run(gateway.action(PLUGIN_ID, "overview", "set_type", {}, "viewer"))
    except PermissionError:
        pass
    else:
        raise AssertionError("viewer must be forbidden")


def test_panels_gateway_validates_ids_and_payloads():
    gateway = WebUIPanelsGateway(FakeAdapter(FakePanelPlugin()))
    for bad_panel in ("", "UPPER", "../etc", "a" * 60, "x-y"):
        try:
            asyncio.run(gateway.data(PLUGIN_ID, bad_panel))
        except ValueError:
            pass
        else:
            raise AssertionError(f"bad panel id accepted: {bad_panel!r}")
    try:
        asyncio.run(gateway.action(PLUGIN_ID, "overview", "bad action", {}, "owner"))
    except ValueError:
        pass
    else:
        raise AssertionError("bad action id accepted")
    # 非映射 payload 视为空对象，不抛错
    result = asyncio.run(gateway.action(PLUGIN_ID, "overview", "set_type", None, "admin"))
    assert result["success"] is True


def test_webui_lifecycle_callable_gates(monkeypatch, tmp_path):
    from test_plugin_entry import context, import_main

    module = import_main(monkeypatch)
    plugin = module.UpdateManagerPlugin(context(tmp_path), {})
    recorded = []

    async def fake_apply(plugin_id, operation, *, force=False):
        recorded.append((plugin_id, operation, force))
        return {"version": "9.9.9", "lifecycle": {"operation": operation}}

    plugin._apply_recommended_plugin = fake_apply

    # 不可信插件 → 拒绝
    try:
        asyncio.run(plugin._webui_lifecycle("not_a_plugin", "update"))
    except LookupError:
        pass
    else:
        raise AssertionError("untrusted plugin must be rejected")

    # 核自身 → 禁止
    try:
        asyncio.run(plugin._webui_lifecycle(module.PLUGIN_NAME, "update"))
    except ValueError as exc:
        assert "SELF_UPDATE_FORBIDDEN" in str(exc)
    else:
        raise AssertionError("self update must be forbidden")

    # force 仅对 update 生效
    result = asyncio.run(
        plugin._webui_lifecycle(PLUGIN_ID, "update", force=True)
    )
    assert recorded[-1] == (PLUGIN_ID, "update", True)
    assert result["version"] == "9.9.9"

    asyncio.run(plugin._webui_lifecycle(PLUGIN_ID, "disable", force=True))
    assert recorded[-1] == (PLUGIN_ID, "disable", False)


def _make_server(tmp_path, *, panels=None, lifecycle=None):
    (tmp_path / "index.html").write_text("standalone", encoding="utf-8")
    auth = WebUIAuth(AtomicJsonStore(tmp_path / "data"))
    auth.create_admin("owner", "owner-pass", "owner")
    auth.create_admin("admin", "admin-pass", "admin")
    auth.create_admin("viewer", "viewer-pass", "viewer")

    async def modules():
        return {"modules": [{"plugin_id": PLUGIN_ID, "status": "normal"}]}

    async def diagnostics():
        return {"providers": []}

    def model_routing():
        return {"contract": {"name": "series.model_router@1.0"}, "routes": {}}

    return WebUIServer(
        auth,
        static_root=tmp_path,
        host="127.0.0.1",
        port=_free_port(),
        modules=modules,
        diagnostics=diagnostics,
        model_routing=model_routing,
        panels=panels,
        lifecycle=lifecycle,
    )


def _free_port() -> int:
    import socket

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def test_webui_panel_routes_auth_roles_and_dispatch(tmp_path):
    plugin = FakePanelPlugin()
    gateway = WebUIPanelsGateway(FakeAdapter(plugin))

    async def lifecycle(plugin_id, action, *, force=False):
        if plugin_id != PLUGIN_ID:
            raise LookupError("PLUGIN_NOT_TRUSTED")
        return {"plugin_id": plugin_id, "action": action, "version": "1.0.0"}

    server = _make_server(tmp_path, panels=gateway, lifecycle=lifecycle)

    async def exercise():
        await server.start()
        jar = aiohttp.CookieJar(unsafe=True)
        async with aiohttp.ClientSession(cookie_jar=jar) as client:
            base = server.url
            # 未登录：面板与生命周期一律 401
            async with client.get(f"{base}/api/series/{PLUGIN_ID}/panels") as response:
                assert response.status == 401
            async with client.post(
                f"{base}/api/series/{PLUGIN_ID}/lifecycle/update", json={}
            ) as response:
                assert response.status == 401

            async with client.post(
                f"{base}/api/login",
                json={"username": "viewer", "password": "viewer-pass"},
            ) as response:
                assert response.status == 200
            # viewer：面板列表/数据可读，动作 403，生命周期 403
            async with client.get(f"{base}/api/series/{PLUGIN_ID}/panels") as response:
                assert response.status == 200
                payload = await response.json()
                assert payload["panels"][0]["id"] == "overview"
            async with client.get(
                f"{base}/api/series/{PLUGIN_ID}/panels/overview"
            ) as response:
                assert response.status == 200
                payload = await response.json()
                assert payload["rows"][0]["user"] == "1483904397"
            async with client.post(
                f"{base}/api/series/{PLUGIN_ID}/panels/overview/actions/set_type",
                json={"relationship_type": "lover"},
            ) as response:
                assert response.status == 403
            async with client.post(
                f"{base}/api/series/{PLUGIN_ID}/lifecycle/update", json={}
            ) as response:
                assert response.status == 403

            async with client.post(
                f"{base}/api/login",
                json={"username": "admin", "password": "admin-pass"},
            ) as response:
                assert response.status == 200
            # admin：动作放行，生命周期仍 403
            async with client.post(
                f"{base}/api/series/{PLUGIN_ID}/panels/overview/actions/set_type",
                json={"relationship_type": "exclusive"},
            ) as response:
                assert response.status == 200
                payload = await response.json()
                assert payload["applied"] == {"relationship_type": "exclusive"}
            async with client.post(
                f"{base}/api/series/{PLUGIN_ID}/lifecycle/enable", json={}
            ) as response:
                assert response.status == 403

            async with client.post(
                f"{base}/api/login",
                json={"username": "owner", "password": "owner-pass"},
            ) as response:
                assert response.status == 200
            # owner：生命周期放行；非法动作 400；不可信插件 400
            async with client.post(
                f"{base}/api/series/{PLUGIN_ID}/lifecycle/update", json={"force": True}
            ) as response:
                assert response.status == 200
                payload = await response.json()
                assert payload["action"] == "update"
            async with client.post(
                f"{base}/api/series/{PLUGIN_ID}/lifecycle/explode", json={}
            ) as response:
                assert response.status == 400
            async with client.post(
                f"{base}/api/series/not_a_plugin/lifecycle/update", json={}
            ) as response:
                assert response.status == 400
            # 未加载面板（无实例）→ 503
            async with client.get(
                f"{base}/api/series/astrbot_plugin_voice_hub/panels"
            ) as response:
                assert response.status == 503
        await server.stop()

    asyncio.run(exercise())


def test_webui_panel_routes_report_unavailable_when_not_wired(tmp_path):
    server = _make_server(tmp_path)

    async def exercise():
        await server.start()
        jar = aiohttp.CookieJar(unsafe=True)
        async with aiohttp.ClientSession(cookie_jar=jar) as client:
            async with client.post(
                f"{server.url}/api/login",
                json={"username": "owner", "password": "owner-pass"},
            ) as response:
                assert response.status == 200
            async with client.get(
                f"{server.url}/api/series/{PLUGIN_ID}/panels"
            ) as response:
                assert response.status == 503
                payload = await response.json()
                assert payload["error"] == "PANELS_UNAVAILABLE"
            async with client.post(
                f"{server.url}/api/series/{PLUGIN_ID}/lifecycle/update", json={}
            ) as response:
                assert response.status == 503
                payload = await response.json()
                assert payload["error"] == "LIFECYCLE_UNAVAILABLE"
        await server.stop()

    asyncio.run(exercise())


def test_webui_panel_action_failure_returns_500_not_crash(tmp_path):
    gateway = WebUIPanelsGateway(FakeAdapter(FakePanelPlugin(fail_action=True)))
    server = _make_server(tmp_path, panels=gateway)

    async def exercise():
        await server.start()
        jar = aiohttp.CookieJar(unsafe=True)
        async with aiohttp.ClientSession(cookie_jar=jar) as client:
            async with client.post(
                f"{server.url}/api/login",
                json={"username": "owner", "password": "owner-pass"},
            ) as response:
                assert response.status == 200
            async with client.post(
                f"{server.url}/api/series/{PLUGIN_ID}/panels/overview/actions/set_type",
                json={},
            ) as response:
                assert response.status == 500
                payload = await response.json()
                assert payload["error"].startswith("PANEL_FAILED")
        await server.stop()

    asyncio.run(exercise())
