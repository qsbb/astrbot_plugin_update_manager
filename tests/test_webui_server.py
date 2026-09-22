from __future__ import annotations

import asyncio
import socket

import aiohttp

from astrbot_plugin_update_manager.core.adapters.storage import AtomicJsonStore
from astrbot_plugin_update_manager.core.webui_auth import WebUIAuth
from astrbot_plugin_update_manager.core.webui_server import WebUIServer


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def test_standalone_webui_is_independent_from_plugin_page(tmp_path):
    (tmp_path / "index.html").write_text("standalone", encoding="utf-8")
    auth = WebUIAuth(AtomicJsonStore(tmp_path / "data"))
    auth.create_admin("owner", "owner-pass", "owner")

    async def modules():
        return {"modules": [{"plugin_id": "demo", "status": "normal"}]}

    async def diagnostics():
        return {"providers": []}

    def model_routing():
        return {"contract": {"name": "series.model_router@1.0"}, "routes": {}}

    server = WebUIServer(
        auth,
        static_root=tmp_path,
        host="127.0.0.1",
        port=free_port(),
        modules=modules,
        diagnostics=diagnostics,
        model_routing=model_routing,
    )

    async def exercise():
        await server.start()
        jar = aiohttp.CookieJar(unsafe=True)
        async with aiohttp.ClientSession(cookie_jar=jar) as client:
            async with client.get(server.url + "/") as response:
                assert response.status == 200
                assert await response.text() == "standalone"
            async with client.get(server.url + "/static/index.html") as response:
                assert response.status == 200
            async with client.get(server.url + "/api/modules") as response:
                assert response.status == 401
            async with client.get(server.url + "/api/model-routing") as response:
                assert response.status == 401
            async with client.post(
                server.url + "/api/login",
                json={"username": "owner", "password": "owner-pass"},
            ) as response:
                assert response.status == 200
            async with client.get(server.url + "/api/modules") as response:
                assert response.status == 200
                assert (await response.json())["modules"][0]["plugin_id"] == "demo"
            async with client.get(server.url + "/api/model-routing") as response:
                assert response.status == 200
                assert (await response.json())["contract"][
                    "name"
                ] == "series.model_router@1.0"
        await server.stop()

    asyncio.run(exercise())


def test_model_options_route_requires_auth_and_uses_callback(tmp_path):
    (tmp_path / "index.html").write_text("standalone", encoding="utf-8")
    auth = WebUIAuth(AtomicJsonStore(tmp_path / "data"))
    auth.create_admin("owner", "owner-pass", "owner")

    async def model_options():
        return {"capabilities": {"conversation": [{"provider_id": "demo", "models": ["m1"]}]}}

    server = WebUIServer(
        auth,
        static_root=tmp_path,
        host="127.0.0.1",
        port=free_port(),
        modules=lambda: asyncio.sleep(0, result={}),
        diagnostics=lambda: asyncio.sleep(0, result={}),
        model_options=model_options,
    )

    async def exercise():
        await server.start()
        jar = aiohttp.CookieJar(unsafe=True)
        async with aiohttp.ClientSession(cookie_jar=jar) as client:
            async with client.get(server.url + "/api/model-options") as response:
                assert response.status == 401
            async with client.post(
                server.url + "/api/login",
                json={"username": "owner", "password": "owner-pass"},
            ) as response:
                assert response.status == 200
            async with client.get(server.url + "/api/model-options") as response:
                assert response.status == 200
                assert (await response.json())["capabilities"]["conversation"][0]["models"] == ["m1"]
        await server.stop()

    asyncio.run(exercise())


def test_model_routing_test_route_requires_admin_and_uses_callback(tmp_path):
    """测试全部模型：未登录 401、viewer 403、admin 才能真调自检回调。"""
    (tmp_path / "index.html").write_text("standalone", encoding="utf-8")
    auth = WebUIAuth(AtomicJsonStore(tmp_path / "data"))
    auth.create_admin("owner", "owner-pass", "owner")
    auth.create_admin("viewer", "viewer-pass", "viewer")

    calls: list[dict] = []

    async def model_test(payload=None):
        calls.append(payload or {})
        return {"success": True, "results": [{"kind": "fast", "state": "ok", "latency_ms": 5}]}

    server = WebUIServer(
        auth,
        static_root=tmp_path,
        host="127.0.0.1",
        port=free_port(),
        modules=lambda: asyncio.sleep(0, result={}),
        diagnostics=lambda: asyncio.sleep(0, result={}),
        model_test=model_test,
    )

    async def exercise():
        await server.start()
        async with aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar(unsafe=True)) as client:
            async with client.post(server.url + "/api/model-routing/test", json={}) as response:
                assert response.status == 401
        async with aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar(unsafe=True)) as client:
            async with client.post(
                server.url + "/api/login",
                json={"username": "viewer", "password": "viewer-pass"},
            ) as response:
                assert response.status == 200
            async with client.post(server.url + "/api/model-routing/test", json={}) as response:
                assert response.status == 403
        async with aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar(unsafe=True)) as client:
            async with client.post(
                server.url + "/api/login",
                json={"username": "owner", "password": "owner-pass"},
            ) as response:
                assert response.status == 200
            async with client.post(
                server.url + "/api/model-routing/test", json={"kinds": ["fast"]}
            ) as response:
                assert response.status == 200
                assert (await response.json())["results"][0]["state"] == "ok"
        await server.stop()

    asyncio.run(exercise())
    assert calls == [{"kinds": ["fast"]}]


def test_backup_routes_require_admin_and_use_callbacks(tmp_path):
    """备份端点：状态/列表登录可读，立即备份与删除必须 admin。"""
    (tmp_path / "index.html").write_text("standalone", encoding="utf-8")
    auth = WebUIAuth(AtomicJsonStore(tmp_path / "data"))
    auth.create_admin("owner", "owner-pass", "owner")
    auth.create_admin("viewer", "viewer-pass", "viewer")

    calls: list[str] = []

    async def backup_status():
        calls.append("status")
        return {"success": True, "running": False, "enabled": False, "target_dir": "/tmp/backups"}

    async def backup_run():
        calls.append("run")
        return {"success": True, "filename": "astrbot_backup_20260922_033000.zip", "size_bytes": 10}

    async def backup_list():
        calls.append("list")
        return {"success": True, "files": [], "total_bytes": 0}

    async def backup_delete(payload=None):
        calls.append(f"delete:{payload.get('filename') if isinstance(payload, dict) else ''}")
        return {"success": True, "name": "astrbot_backup_old.zip"}

    server = WebUIServer(
        auth,
        static_root=tmp_path,
        host="127.0.0.1",
        port=free_port(),
        modules=lambda: asyncio.sleep(0, result={}),
        diagnostics=lambda: asyncio.sleep(0, result={}),
        backup_status=backup_status,
        backup_run=backup_run,
        backup_list=backup_list,
        backup_delete=backup_delete,
    )

    async def exercise():
        await server.start()
        async with aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar(unsafe=True)) as client:
            async with client.get(server.url + "/api/backup/status") as response:
                assert response.status == 401
        async with aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar(unsafe=True)) as client:
            async with client.post(
                server.url + "/api/login",
                json={"username": "viewer", "password": "viewer-pass"},
            ) as response:
                assert response.status == 200
            async with client.get(server.url + "/api/backup/status") as response:
                assert response.status == 200
            async with client.get(server.url + "/api/backup/list") as response:
                assert response.status == 200
            async with client.post(server.url + "/api/backup/run") as response:
                assert response.status == 403
            async with client.post(
                server.url + "/api/backup/delete", json={"filename": "x.zip"}
            ) as response:
                assert response.status == 403
        async with aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar(unsafe=True)) as client:
            async with client.post(
                server.url + "/api/login",
                json={"username": "owner", "password": "owner-pass"},
            ) as response:
                assert response.status == 200
            async with client.post(server.url + "/api/backup/run") as response:
                assert response.status == 200
                assert (await response.json())["filename"].endswith(".zip")
            async with client.post(
                server.url + "/api/backup/delete",
                json={"filename": "astrbot_backup_old.zip"},
            ) as response:
                assert response.status == 200
        await server.stop()

    asyncio.run(exercise())
    assert calls == ["status", "list", "run", "delete:astrbot_backup_old.zip"]


def test_wildcard_webui_url_uses_dashboard_host_without_wildcard(tmp_path):
    auth = WebUIAuth(AtomicJsonStore(tmp_path / "data"))
    server = WebUIServer(
        auth,
        static_root=tmp_path,
        host="0.0.0.0",
        port=25528,
        modules=lambda: asyncio.sleep(0, result={}),
        diagnostics=lambda: asyncio.sleep(0, result={}),
    )
    assert server.url == "http://127.0.0.1:25528"
    assert server.url_for_host("192.168.5.88:25520") == "http://192.168.5.88:25528"
    assert server.url_for_host("[::1]:25520") == "http://[::1]:25528"
    assert "0.0.0.0" not in server.url_for_host("192.168.5.88:25520")
