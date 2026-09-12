from __future__ import annotations

import asyncio
import socket
import sys
from pathlib import Path

import aiohttp

sys.path.insert(0, str(Path(__file__).resolve().parents[1].parent))

from astrbot_plugin_update_manager.core.adapters.storage import AtomicJsonStore
from astrbot_plugin_update_manager.core.webui_auth import WebUIAuth
from astrbot_plugin_update_manager.core.webui_server import WebUIConflictError, WebUIServer


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def make_server(tmp_path) -> WebUIServer:
    (tmp_path / "index.html").write_text("standalone", encoding="utf-8")
    auth = WebUIAuth(AtomicJsonStore(tmp_path / "data"))
    auth.create_admin("owner", "owner-pass", "owner")
    auth.create_admin("admin", "admin-pass", "admin")
    auth.create_admin("viewer", "viewer-pass", "viewer")
    calls: list[tuple] = []

    async def rules_get():
        return {"success": True, "rule": {"revision": 3, "enabled": True}}

    async def rules_save(payload=None):
        calls.append(("rules_save", payload))
        return {"success": True, "rule": {"revision": 4, "enabled": bool(payload.get("enabled"))}}

    async def mirrors_get():
        return {"success": True, "selected": "https://mirror.test", "candidates": []}

    async def mirrors_benchmark(payload=None):
        calls.append(("mirrors_benchmark", payload))
        return {"success": True, "results": [{"url": "https://mirror.test", "available": True}]}

    async def recommendations_get():
        return {"success": True, "items": [{"plugin_id": "demo"}]}

    async def recommendations_check():
        calls.append(("recommendations_check",))
        return {"success": True, "items": [{"plugin_id": "demo", "update_available": True}]}

    async def recommendations_apply_all(payload=None):
        calls.append(("recommendations_apply_all", payload))
        return {"success": True, "total": 1, "succeeded": 1, "failed": 0}

    async def admins_list():
        return {"success": True, "admins": [{"id": "a1", "username": "owner", "role": "owner", "enabled": True}]}

    async def admins_create(payload=None):
        calls.append(("admins_create", payload))
        return {"success": True, "admin": {"id": "a2", "username": payload["username"], "role": payload["role"], "enabled": True}}

    async def admins_update(payload=None):
        calls.append(("admins_update", payload))
        return {"success": True, "admin": {"id": payload["admin_id"], "username": "owner", "role": payload.get("role", "owner"), "enabled": payload.get("enabled", True)}}

    return WebUIServer(
        auth,
        static_root=tmp_path,
        host="127.0.0.1",
        port=free_port(),
        modules=lambda: asyncio.sleep(0, result={"modules": []}),
        diagnostics=lambda: asyncio.sleep(0, result={"providers": []}),
        rules_get=rules_get,
        rules_save=rules_save,
        mirrors_get=mirrors_get,
        mirrors_benchmark=mirrors_benchmark,
        recommendations_get=recommendations_get,
        recommendations_check=recommendations_check,
        recommendations_apply_all=recommendations_apply_all,
        admins_list=admins_list,
        admins_create=admins_create,
        admins_update=admins_update,
    )


def test_webui_control_plane_role_gates_and_crud(tmp_path):
    server = make_server(tmp_path)

    async def exercise():
        await server.start()
        jar = aiohttp.CookieJar(unsafe=True)
        async with aiohttp.ClientSession(cookie_jar=jar) as client:
            async with client.get(server.url + "/api/rules") as response:
                assert response.status == 401
            async with client.post(
                server.url + "/api/login",
                json={"username": "viewer", "password": "viewer-pass"},
            ) as response:
                assert response.status == 200
            assert (await client.get(server.url + "/api/rules")).status == 200
            assert (await client.post(server.url + "/api/rules", json={})).status == 403
            assert (await client.post(server.url + "/api/recommendations/check", json={})).status == 403
            assert (await client.post(server.url + "/api/recommendations/apply-all", json={"confirm": True})).status == 403
            assert (await client.get(server.url + "/api/admins")).status == 403

            async with client.post(
                server.url + "/api/login",
                json={"username": "admin", "password": "admin-pass"},
            ) as response:
                assert response.status == 200
            async with client.post(
                server.url + "/api/rules", json={"enabled": False}
            ) as response:
                assert response.status == 200
            async with client.post(
                server.url + "/api/mirrors/benchmark", json={"mirrors": []}
            ) as response:
                assert response.status == 200
            async with client.post(
                server.url + "/api/recommendations/check", json={}
            ) as response:
                assert response.status == 200
            assert (await client.post(server.url + "/api/recommendations/apply-all", json={"confirm": True})).status == 403
            assert (await client.get(server.url + "/api/admins")).status == 403

            async with client.post(
                server.url + "/api/login",
                json={"username": "owner", "password": "owner-pass"},
            ) as response:
                assert response.status == 200
            async with client.post(
                server.url + "/api/recommendations/apply-all", json={"confirm": True}
            ) as response:
                assert response.status == 200
            async with client.get(server.url + "/api/admins") as response:
                assert response.status == 200
                assert (await response.json())["admins"][0]["role"] == "owner"
            async with client.post(
                server.url + "/api/admins/create",
                json={"username": "new-admin", "password": "new-pass-1", "role": "admin"},
            ) as response:
                assert response.status == 200
            async with client.post(
                server.url + "/api/admins/update",
                json={"admin_id": "a2", "role": "viewer", "enabled": False},
            ) as response:
                assert response.status == 200
        await server.stop()

    asyncio.run(exercise())


def test_webui_control_plane_unavailable_without_callbacks(tmp_path):
    (tmp_path / "index.html").write_text("standalone", encoding="utf-8")
    auth = WebUIAuth(AtomicJsonStore(tmp_path / "data"))
    auth.create_admin("owner", "owner-pass", "owner")
    server = WebUIServer(
        auth,
        static_root=tmp_path,
        host="127.0.0.1",
        port=free_port(),
        modules=lambda: asyncio.sleep(0, result={"modules": []}),
        diagnostics=lambda: asyncio.sleep(0, result={"providers": []}),
    )

    async def exercise():
        await server.start()
        jar = aiohttp.CookieJar(unsafe=True)
        async with aiohttp.ClientSession(cookie_jar=jar) as client:
            async with client.post(
                server.url + "/api/login",
                json={"username": "owner", "password": "owner-pass"},
            ):
                pass
            for method, path in (
                ("GET", "/api/rules"),
                ("POST", "/api/rules"),
                ("GET", "/api/mirrors"),
                ("POST", "/api/mirrors/benchmark"),
                ("GET", "/api/recommendations"),
                ("POST", "/api/recommendations/check"),
                ("POST", "/api/recommendations/apply-all"),
                ("GET", "/api/admins"),
                ("POST", "/api/admins/create"),
                ("POST", "/api/admins/update"),
            ):
                async with client.request(method, server.url + path, json={}) as response:
                    assert response.status == 503, path
                    assert (await response.json())["error"].endswith("_UNAVAILABLE")
        await server.stop()

    asyncio.run(exercise())


def test_webui_control_plane_maps_optimistic_conflict_to_409(tmp_path):
    (tmp_path / "index.html").write_text("standalone", encoding="utf-8")
    auth = WebUIAuth(AtomicJsonStore(tmp_path / "data"))
    auth.create_admin("owner", "owner-pass", "owner")

    async def conflict(payload=None):
        raise WebUIConflictError("RULE_REVISION_CONFLICT")

    server = WebUIServer(
        auth,
        static_root=tmp_path,
        host="127.0.0.1",
        port=free_port(),
        modules=lambda: asyncio.sleep(0, result={"modules": []}),
        diagnostics=lambda: asyncio.sleep(0, result={"providers": []}),
        rules_save=conflict,
    )

    async def exercise():
        await server.start()
        jar = aiohttp.CookieJar(unsafe=True)
        async with aiohttp.ClientSession(cookie_jar=jar) as client:
            async with client.post(
                server.url + "/api/login",
                json={"username": "owner", "password": "owner-pass"},
            ):
                pass
            async with client.post(server.url + "/api/rules", json={}) as response:
                assert response.status == 409
                assert (await response.json())["error"] == "RULE_REVISION_CONFLICT"
        await server.stop()

    asyncio.run(exercise())
