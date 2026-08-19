"""Standalone aiohttp server for the update-manager control center."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Awaitable, Callable
from urllib.parse import urlsplit

from aiohttp import web

from .webui_auth import WebUIAuth, WebUIAuthError

SESSION_COOKIE = "nx_update_manager_session"


class WebUIServer:
    """Serve the control center outside AstrBot's embedded Plugin Page."""

    def __init__(
        self,
        auth: WebUIAuth,
        *,
        static_root: Path,
        host: str,
        port: int,
        public_url: str = "",
        modules: Callable[[], Awaitable[dict[str, Any]]],
        diagnostics: Callable[[], Awaitable[dict[str, Any]]],
    ) -> None:
        self.auth = auth
        self.static_root = static_root.resolve()
        self.host = host
        self.port = port
        candidate_url = public_url.strip().rstrip("/")
        parsed_url = urlsplit(candidate_url) if candidate_url else None
        self.public_url = (
            candidate_url
            if parsed_url
            and parsed_url.scheme in {"http", "https"}
            and parsed_url.hostname
            and not parsed_url.username
            and not parsed_url.password
            and not parsed_url.query
            and not parsed_url.fragment
            else ""
        )
        self.modules = modules
        self.diagnostics = diagnostics
        self._runner: web.AppRunner | None = None
        self._site: web.TCPSite | None = None
        self._started = False
        self._lock = asyncio.Lock()

    @property
    def started(self) -> bool:
        return self._started

    @property
    def url(self) -> str:
        if self.public_url:
            return self.public_url
        display_host = "127.0.0.1" if self.host in {"0.0.0.0", "::"} else self.host
        return f"http://{display_host}:{self.port}"

    async def start(self) -> bool:
        async with self._lock:
            if self._started:
                return True
            app = web.Application()
            app.router.add_get("/", self._index)
            app.router.add_get("/static/{path:.*}", self._static)
            app.router.add_post("/api/login", self._login)
            app.router.add_post("/api/logout", self._logout)
            app.router.add_get("/api/session", self._session)
            app.router.add_get("/api/modules", self._modules)
            app.router.add_post("/api/diagnostics", self._diagnostics)
            self._runner = web.AppRunner(app, access_log=None)
            await self._runner.setup()
            self._site = web.TCPSite(self._runner, self.host, self.port)
            await self._site.start()
            self._started = True
            return True

    async def stop(self) -> None:
        async with self._lock:
            self._started = False
            if self._runner is not None:
                await self._runner.cleanup()
            self._runner = None
            self._site = None

    @staticmethod
    def _json(payload: dict[str, Any], status: int = 200) -> web.Response:
        return web.json_response(payload, status=status)

    @staticmethod
    def _cookie(request: web.Request) -> str | None:
        value = request.cookies.get(SESSION_COOKIE)
        return value if isinstance(value, str) and value else None

    def _session_value(self, request: web.Request):
        return self.auth.session(self._cookie(request))

    async def _body(self, request: web.Request) -> dict[str, Any] | None:
        try:
            value = await request.json()
        except (json.JSONDecodeError, TypeError, ValueError):
            return None
        return value if isinstance(value, dict) else None

    async def _index(self, request: web.Request) -> web.StreamResponse:
        return web.FileResponse(self.static_root / "index.html")

    async def _static(self, request: web.Request) -> web.StreamResponse:
        relative = Path(request.match_info["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise web.HTTPNotFound()
        target = (self.static_root / relative).resolve()
        try:
            target.relative_to(self.static_root)
        except ValueError:
            raise web.HTTPNotFound()
        if not target.is_file():
            raise web.HTTPNotFound()
        return web.FileResponse(target)

    async def _login(self, request: web.Request) -> web.Response:
        data = await self._body(request)
        if data is None or set(data) != {"username", "password"}:
            return self._json({"success": False, "error": "INVALID_JSON_PAYLOAD"}, 400)
        try:
            session = self.auth.authenticate(data["username"], data["password"])
        except WebUIAuthError as exc:
            return self._json({"success": False, "error": str(exc)}, 401)
        response = self._json(
            {
                "success": True,
                "session": {"username": session.username, "role": session.role},
            }
        )
        response.set_cookie(
            SESSION_COOKIE,
            session.token,
            httponly=True,
            samesite="Strict",
            secure=self.public_url.startswith("https://"),
            max_age=8 * 60 * 60,
            path="/",
        )
        return response

    async def _logout(self, request: web.Request) -> web.Response:
        self.auth.revoke(self._cookie(request))
        response = self._json({"success": True})
        response.del_cookie(SESSION_COOKIE, path="/")
        return response

    async def _session(self, request: web.Request) -> web.Response:
        session = self._session_value(request)
        if session is None:
            return self._json(
                {
                    "success": True,
                    "authenticated": False,
                    "configured": self.auth.has_enabled_admin(),
                }
            )
        return self._json(
            {
                "success": True,
                "authenticated": True,
                "configured": True,
                "session": {"username": session.username, "role": session.role},
            }
        )

    async def _modules(self, request: web.Request) -> web.Response:
        if self._session_value(request) is None:
            return self._json({"success": False, "error": "AUTH_REQUIRED"}, 401)
        return self._json({"success": True, **await self.modules()})

    async def _diagnostics(self, request: web.Request) -> web.Response:
        if self._session_value(request) is None:
            return self._json({"success": False, "error": "AUTH_REQUIRED"}, 401)
        return self._json({"success": True, **await self.diagnostics()})
