"""独立 WebUI 诊断日志 / 更新检查 / 回滚 / 设置路由测试。"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import aiohttp
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1].parent))

from astrbot_plugin_update_manager.core.adapters.storage import AtomicJsonStore  # noqa: E402
from astrbot_plugin_update_manager.core.webui_auth import WebUIAuth  # noqa: E402
from astrbot_plugin_update_manager.core.webui_server import WebUIServer  # noqa: E402

PLUGIN_ID = "astrbot_plugin_relationship"


def _free_port() -> int:
    import socket

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class FakeCaps:
    install_plugin = True
    update_plugin = True
    turn_on_plugin = True
    turn_off_plugin = True


class FakePlugin:
    """实现全部 WebUI 能力回调的桩插件（模拟 UpdateManagerPlugin 的方法集）。"""

    def __init__(self, store: AtomicJsonStore) -> None:
        self.store = store
        self.rolled_back: list[str] = []
        self.saved: list[dict] = []

    async def _diagnostic_logs_core(self, data):
        cursors = data.get("cursors", {})
        after = int(cursors.get(PLUGIN_ID, 0))
        events = [
            {
                "seq": 1 + after,
                "timestamp": "2026-01-01T00:00:0%s" % after,
                "plugin_id": PLUGIN_ID,
                "plugin_name": "情",
                "level": "INFO",
                "code": "TEST_EVENT",
                "summary": f"事件 {1 + after}",
                "details": {},
            }
        ]
        member = {
            "plugin_id": PLUGIN_ID,
            "plugin_name": "情",
            "display_name": "情",
            "status": "ready",
            "next_seq": 2 + after,
            "dropped_before": 0,
            "gap": False,
            "reset": False,
            "stream_id": "",
        }
        return {
            "success": True,
            "contract": "series.diagnostics.aggregate@1.0",
            "events": events,
            "members": [member],
            "count": len(events),
        }, 200

    async def _diagnostic_clear_core(self, data):
        if data.get("confirm") is not True:
            return {"success": False, "error": "CONFIRMATION_REQUIRED"}, 400
        return {"success": True, "cleared": [PLUGIN_ID], "unavailable": []}, 200

    async def _recommendation_payload(self, *, force_refresh, check_versions=True):
        return {
            "success": True,
            "recommendations": [
                {
                    "plugin_id": PLUGIN_ID,
                    "display_name": "情",
                    "version": "0.9.6",
                    "latest_version": "0.10.0",
                    "update_available": True,
                    "version_status": "update_available",
                    "actions": {},
                }
            ],
        }

    async def _webui_updates_check(self) -> dict:
        payload = await self._recommendation_payload(
            force_refresh=True, check_versions=True
        )
        rows = [
            {
                "plugin_id": item["plugin_id"],
                "display_name": item["display_name"],
                "version": item["version"],
                "latest_version": item["latest_version"],
                "update_available": item["update_available"],
                "version_status": item["version_status"],
            }
            for item in payload["recommendations"]
        ]
        self.store.write(
            "webui-version-state.json",
            {
                "checked_at": "2026-01-01T00:00:00+00:00",
                "items": {row["plugin_id"]: {"update_available": row["update_available"], "version_status": row["version_status"], "latest_version": row["latest_version"]} for row in rows},
            },
        )
        return {"success": True, "checked_at": "2026-01-01T00:00:00+00:00", "items": rows}

    async def _webui_transactions(self) -> dict:
        records = []
        for name in self.store.names("tx-"):
            record = self.store.read(name, None)
            if isinstance(record, dict) and record.get("state") == "COMMITTED":
                records.append(
                    {
                        "tx_id": record["tx_id"],
                        "plugin_id": record["plugin_id"],
                        "from_version": record["from_version"],
                        "to_version": record["to_version"],
                        "started_at": record["started_at"],
                    }
                )
        records.sort(key=lambda item: item["started_at"], reverse=True)
        return {"success": True, "transactions": records}

    async def _webui_rollback(self, tx_id: str) -> dict:
        self.rolled_back.append(tx_id)
        return {"success": True, "tx_id": tx_id, "plugin_id": PLUGIN_ID, "state": "ROLLED_BACK", "from_version": "0.10.0", "to_version": "0.9.6"}

    def _public_config(self) -> dict:
        return {
            "model_routing": {"conversation": {"provider_id": "p1", "model": "m1", "voice": ""}},
            "auto_update_enabled": False,
            "log_level": "INFO",
            "webui_host": "0.0.0.0",
            "webui_port": 25528,
            "webui_public_url": "",
        }

    async def _save_config_core(self, data):
        if "github_token" in data:
            return {"success": False, "error": "VALIDATION_FAILED", "fields": {"github_token": "UNKNOWN_FIELD"}}, 400
        self.saved.append(dict(data))
        return {"success": True, "config": self._public_config(), "persisted": {"local": True, "native": True}, "schedule_updated": False, "restart_required": False}, 200

    async def _webui_diagnostic_logs(self, payload=None) -> dict:
        data = payload if isinstance(payload, dict) else {}
        result, status = await self._diagnostic_logs_core(data)
        if status != 200:
            raise ValueError(str(result.get("error") or "DIAGNOSTIC_LOGS_FAILED"))
        return result

    async def _webui_diagnostic_clear(self, payload=None) -> dict:
        data = payload if isinstance(payload, dict) else {}
        result, status = await self._diagnostic_clear_core(data)
        if status != 200:
            error = str(result.get("error") or "DIAGNOSTIC_CLEAR_FAILED")
            if error == "PLUGIN_NOT_TRUSTED":
                raise LookupError(error)
            raise ValueError(error)
        return result

    async def _webui_model_options(self) -> dict:
        return {
            "success": True,
            "capabilities": {
                "conversation": [{"provider_id": "p1", "display_name": "测试模型", "models": ["m1"], "in_use": True}],
                "embedding": [],
                "vision": [],
                "stt": [],
                "tts": [],
            },
        }

    async def _webui_settings_get(self) -> dict:
        return {
            "success": True,
            "settings": self._public_config(),
            "providers": [{"provider_id": "p1", "type": "FakeProvider"}],
        }

    async def _webui_settings_save(self, payload=None) -> dict:
        data = payload if isinstance(payload, dict) else {}
        if not data:
            raise ValueError("INVALID_JSON_PAYLOAD")
        unknown = sorted(set(data) - {"model_routing", "auto_update_enabled", "log_level", "webui_host", "webui_port", "webui_public_url"})
        if unknown:
            raise ValueError(f"UNKNOWN_FIELD:{','.join(unknown)}")
        result, status = await self._save_config_core(data)
        if status != 200:
            raise ValueError(str(result.get("error") or "SETTINGS_SAVE_FAILED"))
        return result


def _make_server(tmp_path, plugin: FakePlugin) -> WebUIServer:
    (tmp_path / "index.html").write_text("standalone", encoding="utf-8")
    auth = WebUIAuth(AtomicJsonStore(tmp_path / "auth-data"))
    auth.create_admin("owner", "owner-pass", "owner")
    auth.create_admin("viewer", "viewer-pass", "viewer")
    return WebUIServer(
        auth,
        static_root=tmp_path,
        host="127.0.0.1",
        port=_free_port(),
        modules=plugin._webui_updates_check,  # 任意可调用即可
        diagnostics=plugin._webui_transactions,
        diagnostic_logs=plugin._webui_diagnostic_logs,
        diagnostic_clear=plugin._webui_diagnostic_clear,
        updates_check=plugin._webui_updates_check,
        transactions=plugin._webui_transactions,
        rollback=plugin._webui_rollback,
        settings_get=plugin._webui_settings_get,
        settings_save=plugin._webui_settings_save,
        model_options=plugin._webui_model_options,
    )


def test_webui_diagnostics_logs_updates_settings_routes(tmp_path):
    store = AtomicJsonStore(tmp_path / "data")
    store.write(
        "tx-abc123.json",
        {
            "tx_id": "abc123",
            "plugin_id": PLUGIN_ID,
            "from_version": "0.9.5",
            "to_version": "0.9.6",
            "started_at": "2026-01-01T00:00:00+00:00",
            "state": "COMMITTED",
        },
    )
    store.write(
        "tx-pending.json",
        {"tx_id": "pending", "plugin_id": PLUGIN_ID, "state": "LOCKED"},
    )
    plugin = FakePlugin(store)
    server = _make_server(tmp_path, plugin)

    async def exercise():
        await server.start()
        jar = aiohttp.CookieJar(unsafe=True)
        async with aiohttp.ClientSession(cookie_jar=jar) as client:
            base = server.url
            # 未登录一律 401
            for method, url, payload in (
                ("POST", f"{base}/api/diagnostics/logs", {}),
                ("POST", f"{base}/api/updates/check", {}),
                ("POST", f"{base}/api/settings", {}),
                ("GET", f"{base}/api/model-options", None),
            ):
                kwargs = {"json": payload} if payload is not None else {}
                async with client.request(method, url, **kwargs) as response:
                    assert response.status == 401, url
            async with client.get(f"{base}/api/updates/transactions") as response:
                assert response.status == 401

            async with client.post(
                f"{base}/api/login",
                json={"username": "viewer", "password": "viewer-pass"},
            ) as response:
                assert response.status == 200
            # viewer：读日志/恢复点/设置可读；清空/检查/保存/回滚被拒
            async with client.post(
                f"{base}/api/diagnostics/logs", json={"cursors": {}, "limit": 10}
            ) as response:
                assert response.status == 200
                payload = await response.json()
                assert payload["events"][0]["summary"] == "事件 1"
                assert payload["members"][0]["next_seq"] == 2
            async with client.get(f"{base}/api/updates/transactions") as response:
                assert response.status == 200
                payload = await response.json()
                assert [tx["tx_id"] for tx in payload["transactions"]] == ["abc123"]
            async with client.get(f"{base}/api/settings") as response:
                assert response.status == 200
                payload = await response.json()
                assert payload["settings"]["log_level"] == "INFO"
                assert payload["providers"][0]["provider_id"] == "p1"
            async with client.get(f"{base}/api/model-options") as response:
                assert response.status == 200
                payload = await response.json()
                assert payload["capabilities"]["conversation"][0]["models"] == ["m1"]
            for method, url, payload in (
                ("POST", f"{base}/api/diagnostics/clear", {"confirm": True}),
                ("POST", f"{base}/api/updates/check", {}),
                ("POST", f"{base}/api/settings", {"log_level": "DEBUG"}),
                ("POST", f"{base}/api/updates/rollback", {"tx_id": "abc123"}),
            ):
                async with client.request(method, url, json=payload) as response:
                    assert response.status == 403, url

            async with client.post(
                f"{base}/api/login",
                json={"username": "owner", "password": "owner-pass"},
            ) as response:
                assert response.status == 200
            # owner：游标续读、清空、检查更新（结果落盘）、设置保存、回滚
            async with client.post(
                f"{base}/api/diagnostics/logs",
                json={"cursors": {PLUGIN_ID: 1}, "limit": 10},
            ) as response:
                assert response.status == 200
                payload = await response.json()
                assert payload["events"][0]["seq"] == 2
            async with client.post(
                f"{base}/api/diagnostics/clear", json={"confirm": True}
            ) as response:
                assert response.status == 200
                assert (await response.json())["cleared"] == [PLUGIN_ID]
            async with client.post(f"{base}/api/updates/check", json={}) as response:
                assert response.status == 200
                payload = await response.json()
                assert payload["items"][0]["update_available"] is True
                persisted = store.read("webui-version-state.json", {})
                assert persisted["items"][PLUGIN_ID]["latest_version"] == "0.10.0"
            async with client.post(
                f"{base}/api/settings",
                json={
                    "model_routing": {"conversation": {"provider_id": "p9", "model": "m9", "voice": ""}},
                    "auto_update_enabled": True,
                    "log_level": "DEBUG",
                    "webui_port": 25529,
                },
            ) as response:
                assert response.status == 200
                assert plugin.saved and plugin.saved[-1]["webui_port"] == 25529
            # 白名单外字段被拒
            async with client.post(
                f"{base}/api/settings", json={"github_token": "x"}
            ) as response:
                assert response.status == 400
                assert "UNKNOWN_FIELD" in (await response.json())["error"]
            async with client.post(
                f"{base}/api/updates/rollback", json={"tx_id": "abc123"}
            ) as response:
                assert response.status == 200
                payload = await response.json()
                assert payload["state"] == "ROLLED_BACK"
            assert plugin.rolled_back == ["abc123"]
        await server.stop()

    asyncio.run(exercise())


def test_webui_capability_routes_report_unavailable_without_wiring(tmp_path):
    (tmp_path / "index.html").write_text("standalone", encoding="utf-8")
    auth = WebUIAuth(AtomicJsonStore(tmp_path / "auth-data"))
    auth.create_admin("owner", "owner-pass", "owner")
    server = WebUIServer(
        auth,
        static_root=tmp_path,
        host="127.0.0.1",
        port=_free_port(),
        modules=lambda: asyncio.sleep(0, result={"modules": []}),
        diagnostics=lambda: asyncio.sleep(0, result={"providers": []}),
    )

    async def exercise():
        await server.start()
        jar = aiohttp.CookieJar(unsafe=True)
        async with aiohttp.ClientSession(cookie_jar=jar) as client:
            async with client.post(
                f"{server.url}/api/login",
                json={"username": "owner", "password": "owner-pass"},
            ) as response:
                assert response.status == 200
            for method, url, payload in (
                ("POST", f"{server.url}/api/diagnostics/logs", {}),
                ("POST", f"{server.url}/api/diagnostics/clear", {"confirm": True}),
                ("POST", f"{server.url}/api/updates/check", {}),
                ("GET", f"{server.url}/api/updates/transactions", None),
                ("POST", f"{server.url}/api/updates/rollback", {"tx_id": "x"}),
                ("GET", f"{server.url}/api/settings", None),
                ("POST", f"{server.url}/api/settings", {"log_level": "DEBUG"}),
            ):
                kwargs = {"json": payload} if payload is not None else {}
                async with client.request(method, url, **kwargs) as response:
                    assert response.status == 503, url
                    assert (await response.json())["error"].endswith("_UNAVAILABLE")
        await server.stop()

    asyncio.run(exercise())


def test_webui_settings_rejects_sensitive_fields(tmp_path):
    plugin = FakePlugin(AtomicJsonStore(tmp_path / "data"))
    try:
        asyncio.run(plugin._webui_settings_save({"proxy": "http://x", "log_level": "DEBUG"}))
    except ValueError as exc:
        assert "UNKNOWN_FIELD" in str(exc)
        assert "proxy" in str(exc)
    else:
        raise AssertionError("sensitive field must be rejected")
    assert plugin.saved == []
