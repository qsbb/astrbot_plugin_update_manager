"""AstrBot Plugin Page 独立管理 API，按运行时能力降级。"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any

try:
    from astrbot.api.web import json_response, request
except ImportError:  # AstrBot < 4.26
    try:
        from quart import jsonify, request
    except ImportError:  # 测试或更旧运行时
        jsonify = request = None

    def json_response(payload: dict[str, Any], status: int = 200):
        if jsonify is None:
            return (payload, status) if status != 200 else payload
        response = jsonify(payload)
        return (response, status) if status != 200 else response


PLUGIN_ID = "astrbot_plugin_update_manager"
SENSITIVE_KEYS = frozenset({"github_token"})
READ_ONLY_KEYS = frozenset({"data_dir", "plugin_root"})


class PagesAPIMixin:
    """为支持 Plugin Pages 的 AstrBot 注册最小管理面 API。"""

    def _register_pages_web_api(self) -> bool:
        register = getattr(self.context, "register_web_api", None)
        if not callable(register):
            return False
        routes = (
            ("overview", self._pages_overview, ["GET"], "更新管理器总览"),
            ("config", self._pages_get_config, ["GET"], "读取更新管理器配置"),
            ("config", self._pages_save_config, ["POST"], "保存更新管理器配置"),
            ("catalog", self._pages_catalog, ["GET"], "查看插件目录"),
        )
        try:
            for name, handler, methods, description in routes:
                register(f"/{PLUGIN_ID}/{name}", handler, methods, description)
        except Exception:
            return False
        return True

    @staticmethod
    def _schema() -> dict[str, dict[str, Any]]:
        path = Path(__file__).with_name("_conf_schema.json")
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}

    def _public_config(self) -> dict[str, Any]:
        public: dict[str, Any] = {}
        for key, field in self._schema().items():
            if key in SENSITIVE_KEYS:
                public[key] = {"configured": bool(self._get(key, ""))}
            else:
                public[key] = self._get(key, field.get("default"))
        return public

    async def _pages_overview(self):
        report = self.adapter.probe_capabilities()
        rule = self.scheduler.load()
        return json_response(
            {
                "success": True,
                "plugin": {
                    "id": PLUGIN_ID,
                    "version": getattr(__import__(self.__module__, fromlist=["__version__"]), "__version__", ""),
                    "enabled": self.enabled,
                    "auto_update_enabled": self.auto_update_enabled,
                    "busy": self.coordinator.busy,
                },
                "runtime": {
                    "plugin_pages": callable(getattr(self.context, "register_web_api", None)),
                    "astrbot_version": str(
                        getattr(self.context, "version", None)
                        or getattr(self.context, "astrbot_version", "")
                    ),
                    "capabilities": {
                        "plugin_manager": report.plugin_manager,
                        "list_plugins": report.list_plugins,
                        "install_sources": report.install_sources,
                        "update_plugin": report.update_plugin,
                        "reload_plugin": report.reload_plugin,
                        "cron": report.cron_add_basic_job,
                    },
                },
                "rule": {
                    "enabled": rule.enabled,
                    "revision": rule.revision,
                    "plugins": list(rule.plugin_ids),
                    "next_run": self.scheduler.next_run(rule),
                },
            }
        )

    async def _pages_get_config(self):
        schema = self._schema()
        for key in SENSITIVE_KEYS:
            if key in schema:
                schema[key] = {**schema[key], "write_only": True}
        return json_response(
            {"success": True, "config": self._public_config(), "schema": schema}
        )

    async def _request_json(self) -> Any:
        if request is None:
            return None
        json_reader = getattr(request, "json", None)
        if callable(json_reader):
            value = json_reader(default={})
        else:
            get_json = getattr(request, "get_json", None)
            if not callable(get_json):
                return None
            value = get_json(force=True)
        if inspect.isawaitable(value):
            value = await value
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                return None
        return value

    async def _pages_save_config(self):
        data = await self._request_json()
        if not isinstance(data, dict):
            return json_response(
                {"success": False, "error": "INVALID_JSON_PAYLOAD"}, status=400
            )
        schema = self._schema()
        changes: dict[str, Any] = {}
        errors: dict[str, str] = {}
        for key, value in data.items():
            if key not in schema:
                errors[key] = "UNKNOWN_FIELD"
                continue
            if key in READ_ONLY_KEYS:
                errors[key] = "RESTART_ONLY_FIELD"
                continue
            if key in SENSITIVE_KEYS and value in (None, "", "********"):
                continue
            try:
                changes[key] = self._coerce_page_value(key, value, schema[key])
            except (TypeError, ValueError):
                errors[key] = "INVALID_VALUE"
        if errors:
            return json_response(
                {"success": False, "error": "VALIDATION_FAILED", "fields": errors},
                status=400,
            )

        updated_overrides = {**self._config_overrides, **changes}
        try:
            self.store.write("manager-config.json", updated_overrides)
        except Exception as exc:
            return json_response(
                {
                    "success": False,
                    "error": "CONFIG_PERSIST_FAILED",
                    "detail": str(exc) or type(exc).__name__,
                },
                status=500,
            )

        self._config_overrides = updated_overrides
        native_saved = False
        if self._native_config is not None:
            try:
                self._native_config.update(changes)
                self._native_config.save_config()
                native_saved = True
            except Exception:
                native_saved = False
        try:
            self._apply_page_runtime_config()
        except Exception as exc:
            return json_response(
                {
                    "success": False,
                    "error": "CONFIG_APPLY_FAILED",
                    "detail": str(exc) or type(exc).__name__,
                    "persisted": {"local": True, "native": native_saved},
                },
                status=500,
            )

        schedule_updated = False
        if {"enabled", "auto_update_enabled"} & changes.keys():
            try:
                if self.enabled and self.auto_update_enabled:
                    await self.scheduler.rebuild()
                else:
                    await self.scheduler.remove_job()
                schedule_updated = True
            except Exception as exc:
                return json_response(
                    {
                        "success": False,
                        "error": "SCHEDULE_UPDATE_FAILED",
                        "detail": str(exc) or type(exc).__name__,
                        "config": self._public_config(),
                        "persisted": {"local": True, "native": native_saved},
                    },
                    status=500,
                )
        return json_response(
            {
                "success": True,
                "config": self._public_config(),
                "persisted": {"local": True, "native": native_saved},
                "schedule_updated": schedule_updated,
                "restart_required": False,
            }
        )

    @staticmethod
    def _coerce_page_value(key: str, value: Any, field: dict[str, Any]) -> Any:
        kind = field.get("type")
        if kind == "bool":
            if isinstance(value, bool):
                return value
            if isinstance(value, str) and value.lower() in {"true", "false"}:
                return value.lower() == "true"
            raise ValueError(key)
        if kind == "int":
            value = int(value)
            if value < 0:
                raise ValueError(key)
            return value
        if kind == "float":
            value = float(value)
            if value < 0:
                raise ValueError(key)
            return value
        if kind == "string":
            value = str(value)
            options = field.get("options")
            if options and value not in options:
                raise ValueError(key)
            return value
        raise TypeError(key)

    def _apply_page_runtime_config(self) -> None:
        self.enabled = self._get_bool("enabled", True)
        self.auto_update_enabled = self._get_bool("auto_update_enabled", False)
        self.planner.ttl_seconds = int(self._get("plan_ttl_seconds", 900))
        self.registry.timeout = type(self.registry.timeout)(
            total=int(self._get("network_timeout_seconds", 15))
        )
        self.registry.cache_ttl = int(self._get("cache_ttl_seconds", 300))
        self.registry.proxy = str(self._get("proxy", ""))
        self.registry.github_token = str(self._get("github_token", ""))
        self.transaction.health.stability_seconds = max(
            0.0, float(self._get("health_stability_seconds", 2.0))
        )
        self._apply_log_level(str(self._get("log_level", "INFO")))

    async def _pages_catalog(self):
        items = await self.catalog.scan()
        report = self.adapter.last_discovery_report
        diagnostics = list(report.diagnostics)
        if not items:
            if report.roots_checked == 0:
                diagnostics.append("DISCOVERY_UNAVAILABLE")
            else:
                diagnostics.append("NO_PLUGIN_METADATA_FOUND")
        return json_response(
            {
                "success": True,
                "diagnostics": {
                    "runtime_count": report.runtime_count,
                    "discovered_count": report.discovered_count,
                    "roots_checked": report.roots_checked,
                    "messages": sorted(set(diagnostics)),
                },
                "items": [
                    {
                        "plugin_id": item.plugin_id,
                        "name": getattr(
                            item, "display_name", getattr(item, "name", item.plugin_id)
                        ),
                        "version": item.current_version,
                        "activated": item.activated,
                        "loaded": item.loaded,
                        "eligible": item.eligible,
                        "reasons": list(item.reasons),
                        "source_kind": item.source_kind,
                        "source_url": item.source_url,
                    }
                    for item in items
                ],
            }
        )
