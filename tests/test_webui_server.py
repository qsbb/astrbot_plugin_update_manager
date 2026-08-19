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

    server = WebUIServer(
        auth,
        static_root=tmp_path,
        host="127.0.0.1",
        port=free_port(),
        modules=modules,
        diagnostics=diagnostics,
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
            async with client.post(
                server.url + "/api/login",
                json={"username": "owner", "password": "owner-pass"},
            ) as response:
                assert response.status == 200
            async with client.get(server.url + "/api/modules") as response:
                assert response.status == 200
                assert (await response.json())["modules"][0]["plugin_id"] == "demo"
        await server.stop()

    asyncio.run(exercise())
