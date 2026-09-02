"""Standalone aiohttp server for the update-manager control center."""

from __future__ import annotations

import asyncio
import inspect
import json
from pathlib import Path
from typing import Any, Awaitable, Callable
from urllib.parse import urlsplit

from aiohttp import web

from .transaction import TransactionError

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
        model_routing: Callable[[], dict[str, Any] | Awaitable[dict[str, Any]]]
        | None = None,
        series_control: Any | None = None,
        panels: Any | None = None,
        lifecycle: Callable[..., Awaitable[dict[str, Any]]] | None = None,
        diagnostic_logs: Callable[..., Awaitable[dict[str, Any]]] | None = None,
        diagnostic_clear: Callable[..., Awaitable[dict[str, Any]]] | None = None,
        updates_check: Callable[[], Awaitable[dict[str, Any]]] | None = None,
        transactions: Callable[[], Awaitable[dict[str, Any]]] | None = None,
        rollback: Callable[..., Awaitable[dict[str, Any]]] | None = None,
        settings_get: Callable[[], Awaitable[dict[str, Any]]] | None = None,
        settings_save: Callable[..., Awaitable[dict[str, Any]]] | None = None,
        model_options: Callable[[], Awaitable[dict[str, Any]]] | None = None,
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
        self.model_routing = model_routing
        self.series_control = series_control
        self.panels = panels
        self.lifecycle = lifecycle
        self.diagnostic_logs = diagnostic_logs
        self.diagnostic_clear = diagnostic_clear
        self.updates_check = updates_check
        self.transactions = transactions
        self.rollback = rollback
        self.settings_get = settings_get
        self.settings_save = settings_save
        self.model_options = model_options
        self._runner: web.AppRunner | None = None
        self._site: web.TCPSite | None = None
        self._started = False
        self._lock = asyncio.Lock()

    @property
    def started(self) -> bool:
        return self._started

    @property
    def url(self) -> str:
        return self.url_for_host()

    def url_for_host(self, host: str | None = None) -> str:
        """Return a browser-reachable URL without exposing the wildcard bind address."""
        if self.public_url:
            return self.public_url
        display_host = (host or "").strip()
        if not display_host:
            display_host = "127.0.0.1" if self.host in {"0.0.0.0", "::"} else self.host
        parsed = urlsplit(f"//{display_host}")
        hostname = parsed.hostname
        if not hostname:
            hostname = "127.0.0.1" if self.host in {"0.0.0.0", "::"} else self.host
        rendered_host = (
            f"[{hostname}]"
            if ":" in hostname and not hostname.startswith("[")
            else hostname
        )
        return f"http://{rendered_host}:{self.port}"

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
            app.router.add_get("/api/model-routing", self._model_routing)
            app.router.add_get("/api/series/control", self._series_overview)
            app.router.add_post("/api/series/control/mode", self._series_mode)
            app.router.add_get("/api/series/{plugin_id}/control/schema", self._series_schema)
            app.router.add_get("/api/series/{plugin_id}/control/snapshot", self._series_snapshot)
            app.router.add_post("/api/series/{plugin_id}/control/validate", self._series_validate)
            app.router.add_post("/api/series/{plugin_id}/control/apply", self._series_apply)
            app.router.add_post("/api/series/{plugin_id}/control/reset", self._series_reset)
            app.router.add_get("/api/series/{plugin_id}/control/diagnostics", self._series_diagnostics)
            app.router.add_get("/api/series/{plugin_id}/panels", self._panels_list)
            app.router.add_get("/api/series/{plugin_id}/panels/{panel}", self._panels_data)
            app.router.add_post("/api/series/{plugin_id}/panels/{panel}/actions/{action}", self._panels_action)
            app.router.add_post("/api/series/{plugin_id}/lifecycle/{action}", self._lifecycle_action)
            app.router.add_post("/api/diagnostics/logs", self._diagnostics_logs)
            app.router.add_post("/api/diagnostics/clear", self._diagnostics_clear)
            app.router.add_post("/api/updates/check", self._updates_check)
            app.router.add_get("/api/updates/transactions", self._updates_transactions)
            app.router.add_post("/api/updates/rollback", self._updates_rollback)
            app.router.add_get("/api/settings", self._settings_get)
            app.router.add_post("/api/settings", self._settings_save)
            app.router.add_get("/api/model-options", self._model_options)
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

    async def _model_routing(self, request: web.Request) -> web.Response:
        if self._session_value(request) is None:
            return self._json({"success": False, "error": "AUTH_REQUIRED"}, 401)
        if self.model_routing is None:
            return self._json(
                {"success": False, "error": "MODEL_ROUTER_UNAVAILABLE"}, 503
            )
        try:
            payload = self.model_routing()
            if inspect.isawaitable(payload):
                payload = await payload
        except Exception:
            return self._json(
                {"success": False, "error": "MODEL_ROUTER_UNAVAILABLE"}, 503
            )
        if not isinstance(payload, dict):
            return self._json(
                {"success": False, "error": "MODEL_ROUTER_UNAVAILABLE"}, 503
            )
        return self._json({"success": True, **payload})

    def _series_role(self, request: web.Request) -> str | None:
        session = self._session_value(request)
        return None if session is None else str(session.role)

    async def _series_call(self, request: web.Request, method: str, *args: Any) -> web.Response:
        role = self._series_role(request)
        if role is None:
            return self._json({"success": False, "error": "AUTH_REQUIRED"}, 401)
        if self.series_control is None:
            return self._json({"success": False, "error": "SERIES_CONTROL_UNAVAILABLE"}, 503)
        try:
            function = getattr(self.series_control, method)
            value = function(*args, role=role) if method in {"apply", "reset", "set_mode"} else function(*args)
            if inspect.isawaitable(value):
                value = await value
            return self._json(value if isinstance(value, dict) else {"success": True, "data": value})
        except PermissionError as exc:
            return self._json({"success": False, "error": str(exc)}, 403)
        except (LookupError, ValueError, RuntimeError, TypeError) as exc:
            error = str(exc) or "SERIES_CONTROL_FAILED"
            status = 409 if error == "REVISION_CONFLICT" else 400
            if error in {"PLUGIN_NOT_LOADED", "CONTRACT_UNAVAILABLE", "CONTRACT_VERSION_UNSUPPORTED"}:
                status = 503
            return self._json({"success": False, "error": error}, status)

    async def _series_overview(self, request: web.Request) -> web.Response:
        if self._session_role(request) is None:
            return self._json({"success": False, "error": "AUTH_REQUIRED"}, 401)
        if self.series_control is None:
            return self._json({"success": False, "error": "SERIES_CONTROL_UNAVAILABLE"}, 503)
        return self._json({"success": True, **await self.series_control.overview()})

    def _session_role(self, request: web.Request) -> str | None:
        session = self._session_value(request)
        return None if session is None else str(session.role)

    async def _series_mode(self, request: web.Request) -> web.Response:
        body = await self._body(request)
        if body is None or not isinstance(body.get("mode"), str):
            return self._json({"success": False, "error": "INVALID_JSON_PAYLOAD"}, 400)
        return await self._series_call(request, "set_mode", body["mode"])

    async def _series_schema(self, request: web.Request) -> web.Response:
        return await self._series_call(request, "schema", request.match_info["plugin_id"])

    async def _series_snapshot(self, request: web.Request) -> web.Response:
        return await self._series_call(request, "snapshot", request.match_info["plugin_id"])

    async def _series_diagnostics(self, request: web.Request) -> web.Response:
        return await self._series_call(request, "diagnostics", request.match_info["plugin_id"])

    async def _series_validate(self, request: web.Request) -> web.Response:
        body = await self._body(request)
        if body is None or not isinstance(body.get("patch"), dict):
            return self._json({"success": False, "error": "INVALID_JSON_PAYLOAD"}, 400)
        try:
            revision = int(body.get("expected_revision"))
        except (TypeError, ValueError):
            return self._json({"success": False, "error": "INVALID_REVISION"}, 400)
        return await self._series_call(request, "validate", request.match_info["plugin_id"], body["patch"], revision)

    async def _series_apply(self, request: web.Request) -> web.Response:
        body = await self._body(request)
        if body is None or not isinstance(body.get("patch"), dict):
            return self._json({"success": False, "error": "INVALID_JSON_PAYLOAD"}, 400)
        try:
            revision = int(body.get("expected_revision"))
        except (TypeError, ValueError):
            return self._json({"success": False, "error": "INVALID_REVISION"}, 400)
        return await self._series_call(request, "apply", request.match_info["plugin_id"], body["patch"], revision)

    async def _series_reset(self, request: web.Request) -> web.Response:
        body = await self._body(request)
        fields = body.get("fields") if isinstance(body, dict) else None
        if fields is not None and (not isinstance(fields, list) or not all(isinstance(x, str) for x in fields)):
            return self._json({"success": False, "error": "INVALID_FIELDS"}, 400)
        return await self._series_call(request, "reset", request.match_info["plugin_id"], fields)

    async def _panels_dispatch(
        self, request: web.Request, method: str, *args: Any
    ) -> web.Response:
        role = self._series_role(request)
        if role is None:
            return self._json({"success": False, "error": "AUTH_REQUIRED"}, 401)
        if self.panels is None:
            return self._json({"success": False, "error": "PANELS_UNAVAILABLE"}, 503)
        try:
            function = getattr(self.panels, method)
            if method == "action":
                value = await function(
                    request.match_info["plugin_id"],
                    request.match_info["panel"],
                    request.match_info["action"],
                    await self._body(request) or {},
                    role,
                )
            else:
                call_args = (request.match_info["plugin_id"],) + args
                value = await function(*call_args)
            payload = value if isinstance(value, dict) else {"success": True, "data": value}
            payload.setdefault("success", True)
            return self._json(payload)
        except PermissionError as exc:
            return self._json({"success": False, "error": str(exc)}, 403)
        except LookupError as exc:
            error = str(exc) or "PANEL_FAILED"
            status = 503 if error in {"PLUGIN_NOT_LOADED", "CONTRACT_UNAVAILABLE", "CONTRACT_VERSION_UNSUPPORTED"} else 400
            return self._json({"success": False, "error": error}, status)
        except (ValueError, TypeError) as exc:
            error = str(exc) or "PANEL_FAILED"
            status = 409 if error == "REVISION_CONFLICT" else 400
            return self._json({"success": False, "error": error}, status)
        except Exception as exc:  # noqa: BLE001 — 独立服务必须兜底，避免拖垮整个 WebUI
            return self._json(
                {"success": False, "error": f"PANEL_FAILED:{type(exc).__name__}"}, 500
            )

    async def _panels_list(self, request: web.Request) -> web.Response:
        return await self._panels_dispatch(request, "panels")

    async def _panels_data(self, request: web.Request) -> web.Response:
        return await self._panels_dispatch(request, "data", request.match_info["panel"])

    async def _panels_action(self, request: web.Request) -> web.Response:
        return await self._panels_dispatch(request, "action")

    async def _lifecycle_action(self, request: web.Request) -> web.Response:
        role = self._series_role(request)
        if role is None:
            return self._json({"success": False, "error": "AUTH_REQUIRED"}, 401)
        if self.lifecycle is None:
            return self._json({"success": False, "error": "LIFECYCLE_UNAVAILABLE"}, 503)
        action = request.match_info["action"]
        if action not in {"install", "update", "enable", "disable"}:
            return self._json({"success": False, "error": "INVALID_LIFECYCLE_ACTION"}, 400)
        body = await self._body(request) or {}
        force = bool(body.get("force")) if isinstance(body, dict) else False
        if role != "owner":
            return self._json({"success": False, "error": "OWNER_REQUIRED"}, 403)
        try:
            value = await self.lifecycle(
                request.match_info["plugin_id"], action, force=force
            )
            payload = value if isinstance(value, dict) else {"success": True, "data": value}
            payload.setdefault("success", True)
            return self._json(payload)
        except PermissionError as exc:
            return self._json({"success": False, "error": str(exc)}, 403)
        except LookupError as exc:
            return self._json({"success": False, "error": str(exc)}, 400)
        except (ValueError, RuntimeError) as exc:
            return self._json({"success": False, "error": str(exc)}, 409)

    async def _call_capability(
        self,
        request: web.Request,
        name: str,
        *args: Any,
        role_required: str = "viewer",
        body: bool = False,
    ) -> web.Response:
        """统一能力调用：会话校验 → 角色门控 → 错误映射。"""
        role = self._series_role(request)
        if role is None:
            return self._json({"success": False, "error": "AUTH_REQUIRED"}, 401)
        ranks = {"viewer": 0, "admin": 1, "owner": 2}
        if ranks.get(role, -1) < ranks[role_required]:
            return self._json({"success": False, "error": "ROLE_FORBIDDEN"}, 403)
        function = getattr(self, name, None)
        if not callable(function):
            return self._json(
                {"success": False, "error": f"{name.upper()}_UNAVAILABLE"}, 503
            )
        try:
            call_args = list(args)
            if body:
                call_args.append(await self._body(request))
            value = await function(*call_args)
            payload = value if isinstance(value, dict) else {"success": True, "data": value}
            payload.setdefault("success", True)
            return self._json(payload)
        except PermissionError as exc:
            return self._json({"success": False, "error": str(exc)}, 403)
        except LookupError as exc:
            return self._json({"success": False, "error": str(exc)}, 400)
        except TransactionError as exc:
            return self._json({"success": False, "error": str(exc)}, 409)
        except ValueError as exc:
            return self._json({"success": False, "error": str(exc)}, 400)
        except Exception as exc:  # noqa: BLE001 — 兜底，避免拖垮整个 WebUI
            return self._json(
                {"success": False, "error": f"WEBUI_CAPABILITY_FAILED:{type(exc).__name__}"},
                500,
            )

    async def _diagnostics_logs(self, request: web.Request) -> web.Response:
        return await self._call_capability(request, "diagnostic_logs", body=True)

    async def _diagnostics_clear(self, request: web.Request) -> web.Response:
        return await self._call_capability(
            request, "diagnostic_clear", body=True, role_required="admin"
        )

    async def _updates_check(self, request: web.Request) -> web.Response:
        return await self._call_capability(
            request, "updates_check", role_required="admin"
        )

    async def _updates_transactions(self, request: web.Request) -> web.Response:
        return await self._call_capability(request, "transactions")

    async def _updates_rollback(self, request: web.Request) -> web.Response:
        role = self._series_role(request)
        if role is None:
            return self._json({"success": False, "error": "AUTH_REQUIRED"}, 401)
        if role != "owner":
            return self._json({"success": False, "error": "OWNER_REQUIRED"}, 403)
        body = await self._body(request) or {}
        tx_id = str(body.get("tx_id") or "").strip() if isinstance(body, dict) else ""
        return await self._call_capability(request, "rollback", tx_id)

    async def _settings_get(self, request: web.Request) -> web.Response:
        return await self._call_capability(request, "settings_get")

    async def _settings_save(self, request: web.Request) -> web.Response:
        return await self._call_capability(
            request, "settings_save", body=True, role_required="admin"
        )

    async def _model_options(self, request: web.Request) -> web.Response:
        return await self._call_capability(request, "model_options")
