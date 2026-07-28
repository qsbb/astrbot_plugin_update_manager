"""AstrBot Plugin Page 独立管理 API，按运行时能力降级。"""

from __future__ import annotations

import asyncio
import inspect
import json
import re
from dataclasses import replace
from datetime import datetime, timezone
from functools import partial
from pathlib import Path
from typing import Any

from packaging.version import InvalidVersion, Version

from .core.adapters.astrbot import AdapterUnavailableError
from .core.adapters.registry import (
    DEFAULT_CACHE_TTL_SECONDS,
    DEFAULT_RAW_TIMEOUT_SECONDS,
    RegistryError,
    normalize_optional_setting,
)
from .core.adapters.storage import redact
from .core.concurrency import (
    DEFAULT_CHECK_CONCURRENCY,
    bounded_gather,
    normalize_concurrency,
)
from .core.mirrors import (
    BENCHMARK_PROBE_URL,
    BUILTIN_MIRRORS,
    DEFAULT_BENCHMARK_TIMEOUT_SECONDS,
    apply_mirror,
    available_mirrors,
    normalize_benchmark_timeout,
    normalize_mirror,
    parse_mirror_candidates,
    resolve_mirror,
)
from .core.models import UpdateRule
from .core.scheduler import RuleConflictError, RuleValidationError
from .core.trusted import TRUSTED_BY_ID, TRUSTED_SERIES

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
RULE_WRITABLE_KEYS = frozenset(
    {
        "enabled",
        "plugin_ids",
        "local_time",
        "timezone",
        "jitter_minutes",
        "policy",
        "prerelease",
        "minimum_release_age_hours",
        "on_failure",
        "misfire_grace_minutes",
    }
)
CAPABILITY_META = {
    "plugin_manager": ("插件管理器", "Plugin manager", "AstrBot 插件管理器实例", "AstrBot plugin manager instance"),
    "list_plugins": ("插件列表", "Plugin catalog", "读取当前插件列表", "Read the current plugin list"),
    "install_sources": ("安装来源", "Install sources", "识别插件安装来源", "Resolve plugin install sources"),
    "install_plugin": ("安装插件", "Install plugin", "通过管理器安装插件", "Install plugins through the manager"),
    "update_plugin": ("更新插件", "Update plugin", "通过管理器更新插件", "Update plugins through the manager"),
    "turn_on_plugin": ("启用插件", "Enable plugin", "启用并热加载插件", "Enable and hot-load plugins"),
    "turn_off_plugin": ("停用插件", "Disable plugin", "停用已加载插件", "Disable loaded plugins"),
    "reload_plugin": ("重载插件", "Reload plugin", "重载插件运行时", "Reload plugin runtime"),
    "cron": ("定时任务", "Cron scheduler", "注册每日规则任务", "Register the daily rule job"),
}


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
            ("mirrors", self._pages_mirrors, ["GET"], "查看 GitHub 加速站候选"),
            (
                "mirrors/benchmark",
                self._pages_benchmark_mirrors,
                ["POST"],
                "并发测速 GitHub 加速站",
            ),
            ("rule", self._pages_get_rule, ["GET"], "读取每日自动更新规则"),
            ("rule", self._pages_save_rule, ["POST"], "保存每日自动更新规则"),
            ("catalog", self._pages_catalog, ["GET"], "查看插件目录"),
            (
                "catalog/check-updates",
                self._pages_check_catalog,
                ["POST"],
                "检查目录插件最新版本",
            ),
            ("catalog/update", self._pages_catalog_update, ["POST"], "更新目录插件"),
            ("catalog/enable", self._pages_catalog_enable, ["POST"], "启用目录插件"),
            ("catalog/disable", self._pages_catalog_disable, ["POST"], "停用目录插件"),
            ("recommendations", self._pages_recommendations, ["GET"], "查看可信系列推荐"),
            (
                "recommendations/check-latest",
                self._pages_check_recommendations,
                ["POST"],
                "强制检查可信系列最新版本",
            ),
            (
                "recommendations/apply-all",
                self._pages_apply_all_recommendations,
                ["POST"],
                "安装或更新全部可信系列插件",
            ),
            ("install", self._pages_install, ["POST"], "安装可信系列插件"),
            ("update", self._pages_update, ["POST"], "更新可信系列插件"),
            ("enable", self._pages_enable, ["POST"], "启用可信系列插件"),
            ("disable", self._pages_disable, ["POST"], "停用可信系列插件"),
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

    @staticmethod
    def _capability_payload(report) -> list[dict[str, Any]]:
        values = {
            "plugin_manager": report.plugin_manager,
            "list_plugins": report.list_plugins,
            "install_sources": report.install_sources,
            "install_plugin": report.install_plugin,
            "update_plugin": report.update_plugin,
            "turn_on_plugin": report.turn_on_plugin,
            "turn_off_plugin": report.turn_off_plugin,
            "reload_plugin": report.reload_plugin,
            "cron": report.cron_add_basic_job,
        }
        return [
            {
                "code": code,
                "available": bool(values[code]),
                "label": {"zh-CN": meta[0], "en-US": meta[1]},
                "comment": {"zh-CN": meta[2], "en-US": meta[3]},
            }
            for code, meta in CAPABILITY_META.items()
        ]

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
                    "capabilities": self._capability_payload(report),
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

    # ------------------------------------------------------------ 镜像加速

    def _mirror_benchmark_timeout(self) -> float:
        """单站测速的墙钟预算；非法值回落到默认，避免页面长时间转圈。"""
        return normalize_benchmark_timeout(
            self._get(
                "mirror_benchmark_timeout_seconds",
                DEFAULT_BENCHMARK_TIMEOUT_SECONDS,
            ),
            default=DEFAULT_BENCHMARK_TIMEOUT_SECONDS,
        )

    def _mirror_payload(self) -> dict[str, Any]:
        """镜像候选快照：内置站、自定义站、当前选中项与测速预算。"""
        custom = parse_mirror_candidates(self._get("github_mirror_candidates", ""))
        selected = resolve_mirror(self._get("github_mirror", ""))
        candidates = available_mirrors(custom)
        # 选中项可能来自历史配置且已不在候选里，仍要在列表中可见并保持勾选。
        if selected and selected not in candidates:
            candidates = candidates + (selected,)
        return {
            "success": True,
            "selected": selected,
            "direct": selected is None,
            "builtin": list(BUILTIN_MIRRORS),
            "custom": list(custom),
            "candidates": [
                {
                    "url": url,
                    "builtin": url in BUILTIN_MIRRORS,
                    "selected": url == selected,
                }
                for url in candidates
            ],
            "probe_url": BENCHMARK_PROBE_URL,
            "benchmark_timeout_seconds": self._mirror_benchmark_timeout(),
        }

    async def _pages_mirrors(self):
        return json_response(self._mirror_payload())

    async def _pages_benchmark_mirrors(self):
        """并发测速候选加速站；单站失败只标记该站不可用，绝不抛栈。"""
        data = await self._request_json()
        requested = data.get("mirrors") if isinstance(data, dict) else None
        if requested is None:
            targets = tuple(item["url"] for item in self._mirror_payload()["candidates"])
        elif isinstance(requested, list):
            targets = parse_mirror_candidates(requested)
        else:
            return json_response(
                {"success": False, "error": "INVALID_FIELD_TYPE:mirrors"}, status=400
            )
        timeout_seconds = self._mirror_benchmark_timeout()

        async def measure(mirror: str) -> dict[str, Any]:
            probe_url = apply_mirror(BENCHMARK_PROBE_URL, mirror)
            available, latency_ms, error = await self.registry.probe_latency(
                probe_url, timeout_seconds=timeout_seconds
            )
            return {
                "url": mirror,
                "available": available,
                "latency_ms": latency_ms,
                "error": error,
            }

        results = await bounded_gather(
            [partial(measure, mirror) for mirror in targets],
            limit=self._version_check_concurrency(),
        )
        return json_response(
            {
                "success": True,
                "results": results,
                "probe_url": BENCHMARK_PROBE_URL,
                "benchmark_timeout_seconds": timeout_seconds,
                "checked_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    async def _rule_payload(self, rule: UpdateRule | None = None) -> dict[str, Any]:
        current = rule or self.scheduler.load()
        catalog = await self.catalog.scan()
        selectable = [
            {
                "plugin_id": item.plugin_id,
                "display_name": item.display_name or item.plugin_id,
                "version": item.current_version,
            }
            for item in catalog
            if item.plugin_id != PLUGIN_ID and item.eligible and item.loaded
        ]
        next_run = self.scheduler.next_run(current)
        return {
            "success": True,
            "rule": current.to_dict(),
            "next_run": next_run.isoformat() if next_run else None,
            "global": {
                "enabled": self.enabled,
                "auto_update_enabled": self.auto_update_enabled,
                "effective": self.enabled
                and self.auto_update_enabled
                and current.enabled,
            },
            "catalog": selectable,
            "policy_note": "CHECK_ONLY_WILL_NOT_UPDATE"
            if current.policy == "check_only"
            else None,
        }

    async def _pages_get_rule(self):
        try:
            return json_response(await self._rule_payload())
        except (RuleValidationError, TypeError) as exc:
            return json_response(
                {
                    "success": False,
                    "error": "RULE_LOAD_FAILED",
                    "detail": str(exc) or type(exc).__name__,
                },
                status=500,
            )

    @staticmethod
    def _coerce_rule_changes(data: dict[str, Any]) -> dict[str, Any]:
        changes: dict[str, Any] = {}
        bool_keys = {"enabled", "prerelease"}
        int_keys = {
            "jitter_minutes",
            "minimum_release_age_hours",
            "misfire_grace_minutes",
        }
        string_keys = {"local_time", "timezone", "policy", "on_failure"}
        for key, value in data.items():
            if key == "expected_revision":
                continue
            if key in bool_keys:
                if not isinstance(value, bool):
                    raise RuleValidationError(f"INVALID_FIELD_TYPE:{key}")
                changes[key] = value
            elif key in int_keys:
                if isinstance(value, bool) or not isinstance(value, int):
                    raise RuleValidationError(f"INVALID_FIELD_TYPE:{key}")
                changes[key] = value
            elif key in string_keys:
                if not isinstance(value, str):
                    raise RuleValidationError(f"INVALID_FIELD_TYPE:{key}")
                changes[key] = value
            elif key == "plugin_ids":
                if not isinstance(value, list) or any(
                    not isinstance(plugin_id, str) for plugin_id in value
                ):
                    raise RuleValidationError("INVALID_FIELD_TYPE:plugin_ids")
                changes[key] = tuple(dict.fromkeys(value))
        return changes

    async def _pages_save_rule(self):
        data = await self._request_json()
        if not isinstance(data, dict):
            return json_response(
                {"success": False, "error": "INVALID_JSON_PAYLOAD"}, status=400
            )
        allowed = RULE_WRITABLE_KEYS | {"expected_revision"}
        unknown = sorted(set(data) - allowed)
        if unknown:
            return json_response(
                {
                    "success": False,
                    "error": "UNKNOWN_RULE_FIELDS",
                    "fields": unknown,
                },
                status=400,
            )
        expected_revision = data.get("expected_revision")
        if isinstance(expected_revision, bool) or not isinstance(expected_revision, int):
            return json_response(
                {"success": False, "error": "EXPECTED_REVISION_REQUIRED"}, status=400
            )
        try:
            current = self.scheduler.load()
            changes = self._coerce_rule_changes(data)
            candidate = replace(current, **changes)
            selected = set(candidate.plugin_ids)
            catalog = {item.plugin_id: item for item in await self.catalog.scan()}
            if PLUGIN_ID in selected:
                raise RuleValidationError("SELF_RULE_TARGET_BLOCKED")
            invalid = sorted(
                plugin_id
                for plugin_id in selected
                if plugin_id not in catalog
                or not catalog[plugin_id].eligible
                or not catalog[plugin_id].loaded
            )
            if invalid:
                raise RuleValidationError(
                    "PLUGIN_NOT_CURRENTLY_ELIGIBLE_OR_LOADED:" + ",".join(invalid)
                )
            saved = self.scheduler.save(
                candidate, expected_revision=expected_revision
            )
            if self.enabled and self.auto_update_enabled and saved.enabled:
                await self.scheduler.rebuild()
                schedule_action = "rebuilt"
            else:
                await self.scheduler.remove_job()
                schedule_action = "removed"
            payload = await self._rule_payload(saved)
            payload["schedule_action"] = schedule_action
            return json_response(payload)
        except RuleConflictError as exc:
            return json_response(
                {
                    "success": False,
                    "error": "RULE_REVISION_CONFLICT",
                    "detail": str(exc),
                    "current_revision": self.scheduler.load().revision,
                },
                status=409,
            )
        except RuleValidationError as exc:
            return json_response(
                {
                    "success": False,
                    "error": str(exc).split(":", 1)[0],
                    "detail": str(exc),
                },
                status=400,
            )
        except Exception as exc:
            return json_response(
                {
                    "success": False,
                    "error": "RULE_SAVE_OR_SCHEDULE_FAILED",
                    "detail": str(exc) or type(exc).__name__,
                },
                status=500,
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
            if key == "github_mirror" and value.strip():
                # 选中的加速站必须是合法 https 前缀，保存即拒绝而不是静默回直连。
                normalized = normalize_mirror(value)
                if normalized is None:
                    raise ValueError(key)
                return normalized
            return value
        raise TypeError(key)

    def _apply_page_runtime_config(self) -> None:
        self.enabled = self._get_bool("enabled", True)
        self.auto_update_enabled = self._get_bool("auto_update_enabled", False)
        self.planner.ttl_seconds = int(self._get("plan_ttl_seconds", 900))
        self.registry.timeout = type(self.registry.timeout)(
            total=int(self._get("network_timeout_seconds", 15))
        )
        self.registry.cache_ttl = int(
            self._get("cache_ttl_seconds", DEFAULT_CACHE_TTL_SECONDS)
        )
        self.registry.raw_timeout_seconds = max(
            1.0,
            float(self._get("raw_timeout_seconds", DEFAULT_RAW_TIMEOUT_SECONDS)),
        )
        self.registry.proxy = normalize_optional_setting(self._get("proxy", ""))
        self.registry.token = normalize_optional_setting(self._get("github_token", ""))
        # 镜像热应用：改完立即生效，非法或留空一律回到直连。
        self.registry.mirror = resolve_mirror(self._get("github_mirror", ""))
        self.transaction.health.stability_seconds = max(
            0.0, float(self._get("health_stability_seconds", 2.0))
        )
        self._apply_log_level(str(self._get("log_level", "INFO")))

    def _catalog_lifecycle(self, item, capabilities) -> dict[str, Any]:
        reason = None
        if not item.loaded:
            reason = "PLUGIN_NOT_LOADED"
        elif "RESERVED_PLUGIN" in item.reasons:
            reason = "RESERVED_PLUGIN"
        elif item.plugin_id == PLUGIN_ID:
            reason = "SELF_LIFECYCLE_BLOCKED"
        can_enable = bool(not reason and capabilities.turn_on_plugin)
        can_disable = bool(not reason and capabilities.turn_off_plugin)
        if not reason and not (can_enable if not item.activated else can_disable):
            reason = "LIFECYCLE_CAPABILITY_UNAVAILABLE"
        return {
            "operable": can_disable if item.activated else can_enable,
            "reason": reason,
        }

    def _catalog_update_lifecycle(self, item, capabilities) -> dict[str, Any]:
        """判断目录项能否被检查版本与更新。

        与启停能力分开算：启停只要插件已加载即可，更新还要求来源可回溯到
        具体的 GitHub 仓库。``registry.github_latest`` 只认
        ``https://github.com/{owner}/{repo}``，market 来源或 URL 缺失的行
        必须在这里就被挡住，不能放进网络调用去换一个必然失败的报错。
        """
        reason = None
        if item.plugin_id == PLUGIN_ID:
            # 自更新会在替换自身代码的过程中打断正在执行的更新流程。
            reason = "SELF_UPDATE_BLOCKED"
        elif "RESERVED_PLUGIN" in item.reasons:
            reason = "RESERVED_PLUGIN"
        elif not item.loaded:
            reason = "PLUGIN_NOT_LOADED"
        elif item.source_kind != "github" or not item.source_url:
            reason = "SOURCE_REQUIRED"
        checkable = reason is None
        if checkable and not capabilities.update_plugin:
            reason = "UPDATE_CAPABILITY_UNAVAILABLE"
        return {
            # 可检查与可更新分开：能力缺失时仍允许查看是否有新版本。
            "checkable": checkable,
            "operable": checkable and bool(capabilities.update_plugin),
            "reason": reason,
        }

    async def _pages_catalog(self):
        items = await self.catalog.scan()
        report = self.adapter.last_discovery_report
        capabilities = self.adapter.probe_capabilities()
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
                        "display_name": item.display_name or item.plugin_id,
                        "version": item.current_version,
                        "activated": item.activated,
                        "loaded": item.loaded,
                        "eligible": item.eligible,
                        "reasons": list(item.reasons),
                        "source_kind": item.source_kind,
                        "source_url": item.source_url,
                        "lifecycle": self._catalog_lifecycle(item, capabilities),
                        # 更新能力随目录一起返回，但不含版本号：GET catalog 保持零网络请求，
                        # 进入页面不会因为几十个插件的版本探测而变慢或消耗 GitHub 配额。
                        "update_lifecycle": self._catalog_update_lifecycle(
                            item, capabilities
                        ),
                    }
                    for item in items
                ],
            }
        )

    async def _pages_check_catalog(self):
        """按需检查目录插件的最新版本。

        只在用户点击「检查更新」时调用，不参与页面初始加载——目录是全量插件
        （可能几十个），无条件全量探测会拖慢首屏并快速耗尽 GitHub 匿名配额。
        可选 ``plugin_ids`` 只检查指定插件，用于更新成功后单项复查。
        """
        data = await self._request_json()
        force_refresh = True
        requested: set[str] | None = None
        if isinstance(data, dict):
            if "force_refresh" in data:
                value = data["force_refresh"]
                if not isinstance(value, bool):
                    return json_response(
                        {"success": False, "error": "INVALID_FIELD_TYPE:force_refresh"},
                        status=400,
                    )
                force_refresh = value
            if data.get("plugin_ids") is not None:
                raw = data["plugin_ids"]
                if not isinstance(raw, list) or not all(
                    isinstance(entry, str) for entry in raw
                ):
                    return json_response(
                        {"success": False, "error": "INVALID_FIELD_TYPE:plugin_ids"},
                        status=400,
                    )
                requested = {entry.strip() for entry in raw if entry.strip()}

        items = await self.catalog.scan()
        capabilities = self.adapter.probe_capabilities()
        targets = [
            item
            for item in items
            if self._catalog_update_lifecycle(item, capabilities)["checkable"]
            and (requested is None or item.plugin_id in requested)
        ]

        async def inspect(item):
            checked_at = datetime.now(timezone.utc).isoformat()
            try:
                candidate = await self._check_latest_with_timeout(
                    item.plugin_id,
                    item.current_version or "",
                    item.source_url or "",
                    force_refresh=force_refresh,
                )
                latest_version = candidate.target_version
                update_available, version_status = self._version_state(
                    item.current_version or "", latest_version
                )
                failure: dict[str, Any] = {
                    "error": None,
                    "error_detail": None,
                    "error_context": {},
                }
            except Exception as exc:
                # 单个仓库探测失败只影响该行，其余插件照常返回版本。
                latest_version = ""
                update_available, version_status = False, "check_failed"
                failure = self._recommendation_error(exc, item.source_url or "")
            return {
                "plugin_id": item.plugin_id,
                "current_version": item.current_version,
                "latest_version": latest_version,
                "update_available": update_available,
                "version_status": version_status,
                "checked_at": checked_at,
                **failure,
            }

        checked = await bounded_gather(
            [partial(inspect, item) for item in targets],
            limit=self._version_check_concurrency(),
        )
        return json_response(
            {
                "success": True,
                "items": list(checked),
                "rate_limit": self.registry.rate_limit_status(),
            }
        )

    async def _catalog_update_target(self):
        """校验目录更新入参并返回目标目录项与强制模式。

        与 ``_catalog_plugin_id`` 同样严格：key 集合精确匹配、强制二次确认、
        必须在册且通过更新资格复核。资格在这里重新算一遍而不是信任前端，
        避免页面数据过期后把不该更新的插件放进来。
        """
        data = await self._request_json()
        if not isinstance(data, dict):
            raise ValueError("INVALID_JSON_PAYLOAD")
        if set(data) not in (
            {"plugin_id", "confirm"},
            {"plugin_id", "confirm", "force"},
        ):
            raise ValueError("CONFIRMATION_REQUIRED")
        if data.get("confirm") is not True:
            raise ValueError("CONFIRMATION_REQUIRED")
        force = data.get("force", False)
        if not isinstance(force, bool):
            raise ValueError("INVALID_FORCE_FLAG")
        plugin_id = data.get("plugin_id")
        if not isinstance(plugin_id, str) or not plugin_id.strip():
            raise ValueError("INVALID_PLUGIN_ID")
        plugin_id = plugin_id.strip()
        if plugin_id == PLUGIN_ID:
            raise ValueError("SELF_UPDATE_BLOCKED")
        catalog = {item.plugin_id: item for item in await self.catalog.scan()}
        item = catalog.get(plugin_id)
        if item is None:
            raise ValueError("PLUGIN_NOT_FOUND")
        lifecycle = self._catalog_update_lifecycle(
            item, self.adapter.probe_capabilities()
        )
        if not lifecycle["operable"]:
            raise ValueError(str(lifecycle["reason"] or "PLUGIN_NOT_MANAGEABLE"))
        return item, force

    async def _pages_catalog_update(self):
        try:
            item, force = await self._catalog_update_target()
            candidate = await self.registry.github_latest(
                item.plugin_id,
                item.current_version or "",
                item.source_url or "",
                force_refresh=True,
            )
            update_available, version_status = self._version_state(
                item.current_version or "", candidate.target_version
            )
            if force:
                if version_status not in {
                    "update_available",
                    "up_to_date",
                    "local_newer",
                }:
                    raise ValueError("FORCE_UPDATE_VERSION_UNAVAILABLE")
            elif not update_available:
                # 普通模式没有新版本就不该触发下载与热重载。
                raise ValueError("NO_UPDATE_AVAILABLE")
            snapshot = await self.adapter.update_plugin(
                item.plugin_id,
                source_kind="github",
                source_url=item.source_url or "",
                archive_url=candidate.archive_url,
            )
            return json_response(
                {
                    "success": True,
                    "plugin_id": item.plugin_id,
                    "updated": True,
                    "forced": force,
                    "version_status": version_status,
                    "version": snapshot.version,
                    "lifecycle": self._lifecycle("update", snapshot),
                }
            )
        except Exception as exc:
            return self._mutation_error(exc)

    async def _catalog_plugin_id(
        self, *, require_confirmation: bool, enabled: bool
    ) -> str:
        data = await self._request_json()
        if not isinstance(data, dict):
            raise ValueError("INVALID_JSON_PAYLOAD")
        expected = {"plugin_id", "confirm"} if require_confirmation else {"plugin_id"}
        if set(data) != expected:
            raise ValueError(
                "CONFIRMATION_REQUIRED" if require_confirmation else "INVALID_JSON_PAYLOAD"
            )
        if require_confirmation and data.get("confirm") is not True:
            raise ValueError("CONFIRMATION_REQUIRED")
        plugin_id = data.get("plugin_id")
        if not isinstance(plugin_id, str) or not plugin_id.strip():
            raise ValueError("INVALID_PLUGIN_ID")
        plugin_id = plugin_id.strip()
        if plugin_id == PLUGIN_ID:
            raise ValueError("SELF_LIFECYCLE_BLOCKED")
        catalog = {item.plugin_id: item for item in await self.catalog.scan()}
        item = catalog.get(plugin_id)
        if item is None:
            raise ValueError("PLUGIN_NOT_FOUND")
        lifecycle = self._catalog_lifecycle(item, self.adapter.probe_capabilities())
        if not lifecycle["operable"]:
            raise ValueError(str(lifecycle["reason"] or "PLUGIN_NOT_MANAGEABLE"))
        if item.activated is enabled:
            raise ValueError("PLUGIN_STATE_UNCHANGED")
        return plugin_id

    async def _set_catalog_enabled(self, enabled: bool):
        try:
            plugin_id = await self._catalog_plugin_id(
                require_confirmation=not enabled, enabled=enabled
            )
            snapshot = await self.adapter.set_plugin_enabled(plugin_id, enabled)
            if snapshot.activated is not enabled or not snapshot.loaded:
                raise RuntimeError("ACTIVATION_RESULT_MISMATCH")
            operation = "enable" if enabled else "disable"
            return json_response(
                {
                    "success": True,
                    "plugin_id": plugin_id,
                    "activated": snapshot.activated,
                    "lifecycle": self._lifecycle(operation, snapshot),
                }
            )
        except Exception as exc:
            return self._mutation_error(exc)

    async def _pages_catalog_enable(self):
        return await self._set_catalog_enabled(True)

    async def _pages_catalog_disable(self):
        return await self._set_catalog_enabled(False)

    async def _trusted_plugin_id(self, *, require_confirmation: bool = True) -> str:
        data = await self._request_json()
        if not isinstance(data, dict):
            raise ValueError("INVALID_JSON_PAYLOAD")
        expected_keys = {"plugin_id", "confirm"} if require_confirmation else {"plugin_id"}
        if set(data) != expected_keys:
            raise ValueError(
                "CONFIRMATION_REQUIRED" if require_confirmation else "INVALID_JSON_PAYLOAD"
            )
        if require_confirmation and data.get("confirm") is not True:
            raise ValueError("CONFIRMATION_REQUIRED")
        plugin_id = data.get("plugin_id")
        if not isinstance(plugin_id, str) or plugin_id not in TRUSTED_BY_ID:
            raise ValueError("PLUGIN_NOT_TRUSTED")
        return plugin_id

    @staticmethod
    def _mutation_error(exc: Exception):
        known = {
            "INVALID_JSON_PAYLOAD": 400,
            "CONFIRMATION_REQUIRED": 400,
            "PLUGIN_NOT_TRUSTED": 403,
            "SELF_UPDATE_BLOCKED": 403,
            "SELF_DISABLE_BLOCKED": 403,
            "SELF_LIFECYCLE_BLOCKED": 403,
            "RESERVED_PLUGIN": 403,
            "INVALID_PLUGIN_ID": 400,
            "INVALID_FORCE_FLAG": 400,
            "PLUGIN_NOT_FOUND": 404,
            "PLUGIN_NOT_LOADED": 409,
            "PLUGIN_STATE_UNCHANGED": 409,
            "LIFECYCLE_CAPABILITY_UNAVAILABLE": 503,
            "PLUGIN_ALREADY_INSTALLED": 409,
            "PLUGIN_NOT_MANAGEABLE": 409,
            "ARCHIVE_URL_REQUIRED": 409,
            "SOURCE_REQUIRED": 409,
            "NO_UPDATE_AVAILABLE": 409,
            "FORCE_UPDATE_VERSION_UNAVAILABLE": 409,
            "UPDATE_CAPABILITY_UNAVAILABLE": 503,
        }
        code = str(exc) if str(exc) in known else type(exc).__name__.upper()
        status = known.get(code, 503 if isinstance(exc, AdapterUnavailableError) else 500)
        return json_response(
            {"success": False, "error": code, "detail": redact(code)}, status=status
        )

    @staticmethod
    def _version_state(current: str, latest: str) -> tuple[bool, str]:
        if not current:
            return False, "not_installed"
        try:
            current_version, latest_version = Version(current), Version(latest)
        except InvalidVersion:
            return False, "unknown"
        if latest_version > current_version:
            return True, "update_available"
        if latest_version == current_version:
            return False, "up_to_date"
        return False, "local_newer"

    def _recommendation_error(self, exc: Exception, repo_url: str) -> dict[str, Any]:
        raw_code = getattr(exc, "code", None) or str(exc) or type(exc).__name__
        code = (
            raw_code
            if re.fullmatch(r"[A-Z][A-Z0-9_]*", raw_code)
            else type(exc).__name__.upper()
        )
        context = exc.to_dict()["context"] if isinstance(exc, RegistryError) else {}
        context.setdefault("repo", repo_url)
        if context.get("rate_limited"):
            # 限流失败必须能回答"多久后可重试"与"如何提额"。
            context.setdefault("token_configured", bool(self.registry.token))
            context["token_hint_required"] = not context["token_configured"]
        detail = redact(str(exc) or type(exc).__name__)
        detail = re.sub(
            r"(?i)\b(?:gh[pousr]_[a-z0-9_]+|bearer\s+\S+)", "***", detail
        )
        return {
            "error": code,
            "error_detail": detail,
            "error_context": context,
        }

    def _version_check_concurrency(self) -> int:
        return normalize_concurrency(
            self._get("version_check_concurrency", DEFAULT_CHECK_CONCURRENCY),
            default=DEFAULT_CHECK_CONCURRENCY,
        )

    def _version_check_timeout(self) -> float:
        """单个插件版本检查的墙钟上限；<=0 表示不额外限制。"""
        try:
            return max(0.0, float(self._get("version_check_timeout_seconds", 25)))
        except (TypeError, ValueError):
            return 25.0

    async def _check_latest_with_timeout(
        self,
        plugin_id: str,
        current_version: str,
        repo_url: str,
        *,
        force_refresh: bool,
    ):
        """给单个插件套一个墙钟上限，慢仓库不能拖住整批检查。"""
        call = self.registry.github_latest(
            plugin_id, current_version, repo_url, force_refresh=force_refresh
        )
        budget = self._version_check_timeout()
        if not budget:
            return await call
        try:
            return await asyncio.wait_for(call, timeout=budget)
        except asyncio.TimeoutError as exc:
            raise RegistryError("VERSION_CHECK_TIMEOUT", repo=repo_url) from exc

    async def _recommendation_payload(self, *, force_refresh: bool) -> dict[str, Any]:
        snapshots = await self.adapter.snapshot_plugins()
        installed = {
            identity: item
            for item in snapshots
            for identity in (item.name, item.root_dir_name)
            if identity
        }
        capabilities = self.adapter.probe_capabilities()

        async def inspect_latest(trusted):
            snapshot = installed.get(trusted.plugin_id)
            checked_at = datetime.now(timezone.utc).isoformat()
            try:
                candidate = await self._check_latest_with_timeout(
                    trusted.plugin_id,
                    snapshot.version if snapshot else "",
                    trusted.repo_url,
                    force_refresh=force_refresh,
                )
                latest_version = candidate.target_version
                update_available, version_status = self._version_state(
                    snapshot.version if snapshot else "", latest_version
                )
                download_url = getattr(candidate, "archive_url", None) or ""
                default_branch = getattr(candidate, "default_branch", None) or ""
                error = None
            except Exception as exc:
                latest_version = ""
                update_available, version_status = False, "check_failed"
                download_url = ""
                default_branch = ""
                failure = self._recommendation_error(exc, trusted.repo_url)
                error = failure["error"]
                error_context = failure["error_context"]
                error_detail = failure["error_detail"]
            else:
                error_context = {}
                error_detail = None
            return trusted, snapshot, {
                "latest_version": latest_version,
                "update_available": update_available,
                "version_status": version_status,
                "download_url": download_url,
                "default_branch": default_branch,
                "checked_at": checked_at,
                "error": error,
                "error_detail": error_detail,
                "error_context": error_context,
            }

        checked = await bounded_gather(
            [partial(inspect_latest, trusted) for trusted in TRUSTED_SERIES],
            limit=self._version_check_concurrency(),
        )
        items = []
        for trusted, snapshot, version_check in checked:
            items.append(
                {
                    "key": trusted.key,
                    "plugin_id": trusted.plugin_id,
                    "name": trusted.display_name,
                    "repo_url": trusted.repo_url,
                    "description_zh": trusted.description_zh,
                    "installed": snapshot is not None,
                    "version": snapshot.version if snapshot else "",
                    "loaded": snapshot.loaded if snapshot else False,
                    "activated": snapshot.activated if snapshot else False,
                    **version_check,
                    "actions": {
                        "install": snapshot is None and capabilities.install_plugin,
                        "update": bool(
                            snapshot
                            and snapshot.loaded
                            and version_check["update_available"]
                            and trusted.plugin_id != PLUGIN_ID
                            and capabilities.update_plugin
                        ),
                        "force_update": bool(
                            snapshot
                            and snapshot.loaded
                            and version_check["version_status"]
                            in {"update_available", "up_to_date", "local_newer"}
                            and trusted.plugin_id != PLUGIN_ID
                            and capabilities.update_plugin
                        ),
                        "enable": bool(
                            snapshot
                            and snapshot.loaded
                            and not snapshot.activated
                            and capabilities.turn_on_plugin
                        ),
                        "disable": bool(
                            snapshot
                            and snapshot.loaded
                            and snapshot.activated
                            and trusted.plugin_id != PLUGIN_ID
                            and capabilities.turn_off_plugin
                        ),
                    },
                }
            )
        self_item = next(
            (item for item in items if item["plugin_id"] == PLUGIN_ID), None
        )
        self_update = None
        if self_item is not None:
            self_update = {
                "current_version": self_item["version"],
                "latest_version": self_item["latest_version"],
                "update_available": self_item["update_available"],
                "version_status": self_item["version_status"],
                "checked_at": self_item["checked_at"],
                "error": self_item["error"],
                "repo_url": self_item["repo_url"],
            }
        rate_limit = (
            self.registry.rate_limit_status()
            if callable(getattr(self.registry, "rate_limit_status", None))
            else None
        )
        return {
            "success": True,
            "items": items,
            "self_update": self_update,
            "rate_limit": rate_limit,
        }

    async def _pages_recommendations(self):
        return json_response(await self._recommendation_payload(force_refresh=False))

    async def _pages_check_recommendations(self):
        # 默认强制刷新（手动"检查最新版本"）；页面自动检查显式传 force_refresh=false 走缓存，避免限流。
        data = await self._request_json()
        force_refresh = True
        if isinstance(data, dict) and "force_refresh" in data:
            value = data["force_refresh"]
            if not isinstance(value, bool):
                return json_response(
                    {"success": False, "error": "INVALID_FIELD_TYPE:force_refresh"},
                    status=400,
                )
            force_refresh = value
        return json_response(
            await self._recommendation_payload(force_refresh=force_refresh)
        )

    @staticmethod
    def _lifecycle(operation: str, snapshot) -> dict[str, Any]:
        return {
            "operation": operation,
            "managed_by": "astrbot_plugin_manager",
            "direct_load": operation == "install",
            "internal_hot_reload": operation in {"update", "enable"},
            "extra_reload": False,
            "extra_reload_performed": False,
            "snapshot_verified": True,
            "snapshot": {
                "version": snapshot.version,
                "loaded": snapshot.loaded,
                "activated": snapshot.activated,
            },
        }

    async def _apply_recommended_plugin(
        self, plugin_id: str, operation: str, *, force: bool = False
    ) -> dict[str, Any]:
        item = TRUSTED_BY_ID[plugin_id]
        if operation == "install":
            if force:
                raise ValueError("INVALID_FORCE_FLAG")
            snapshot = await self.adapter.install_plugin(plugin_id, repo_url=item.repo_url)
            version_status = "not_installed"
        elif operation == "update":
            if plugin_id == PLUGIN_ID:
                raise ValueError("SELF_UPDATE_BLOCKED")
            current = await self.adapter.get_plugin(plugin_id)
            if current is None or not current.loaded:
                raise ValueError("PLUGIN_NOT_MANAGEABLE")
            candidate = await self.registry.github_latest(
                plugin_id,
                current.version,
                item.repo_url,
                force_refresh=True,
            )
            update_available, version_status = self._version_state(
                current.version, candidate.target_version
            )
            if force:
                if version_status not in {
                    "update_available",
                    "up_to_date",
                    "local_newer",
                }:
                    raise ValueError("FORCE_UPDATE_VERSION_UNAVAILABLE")
            elif not update_available:
                raise ValueError("NO_UPDATE_AVAILABLE")
            snapshot = await self.adapter.update_plugin(
                plugin_id,
                source_kind="github",
                source_url=item.repo_url,
                archive_url=candidate.archive_url,
            )
        else:
            raise ValueError("INVALID_OPERATION")
        return {
            "plugin_id": plugin_id,
            "operation": operation,
            "success": True,
            "forced": force,
            "version_status": version_status,
            "version": snapshot.version,
            "lifecycle": self._lifecycle(operation, snapshot),
        }

    async def _pages_apply_all_recommendations(self):
        try:
            data = await self._request_json()
            if not isinstance(data, dict) or set(data) != {"confirm"}:
                raise ValueError("CONFIRMATION_REQUIRED")
            if data.get("confirm") is not True:
                raise ValueError("CONFIRMATION_REQUIRED")

            payload = await self._recommendation_payload(force_refresh=True)
            targets = []
            for item in payload["items"]:
                if item["actions"]["install"]:
                    targets.append((item["plugin_id"], "install"))
                elif item["actions"]["update"]:
                    targets.append((item["plugin_id"], "update"))

            results = []
            for plugin_id, operation in targets:
                try:
                    results.append(await self._apply_recommended_plugin(plugin_id, operation))
                except Exception as exc:
                    error_response = self._mutation_error(exc)
                    error_payload = error_response[0] if isinstance(error_response, tuple) else error_response
                    results.append(
                        {
                            "plugin_id": plugin_id,
                            "operation": operation,
                            "success": False,
                            "error": error_payload.get("error", "UNKNOWN"),
                            "detail": error_payload.get("detail", "UNKNOWN"),
                        }
                    )

            succeeded = sum(1 for result in results if result["success"])
            return json_response(
                {
                    "success": True,
                    "all_succeeded": all(result["success"] for result in results),
                    "total": len(results),
                    "succeeded": succeeded,
                    "failed": len(results) - succeeded,
                    "results": results,
                }
            )
        except Exception as exc:
            return self._mutation_error(exc)

    async def _pages_install(self):
        try:
            plugin_id = await self._trusted_plugin_id()
            result = await self._apply_recommended_plugin(plugin_id, "install")
            return json_response(
                {
                    "success": True,
                    "plugin_id": plugin_id,
                    "installed": True,
                    "version": result["version"],
                    "lifecycle": result["lifecycle"],
                }
            )
        except Exception as exc:
            return self._mutation_error(exc)

    async def _pages_update(self):
        try:
            plugin_id, force = await self._trusted_update_target()
            result = await self._apply_recommended_plugin(
                plugin_id, "update", force=force
            )
            return json_response(
                {
                    "success": True,
                    "plugin_id": plugin_id,
                    "updated": True,
                    "forced": result["forced"],
                    "version_status": result["version_status"],
                    "version": result["version"],
                    "lifecycle": result["lifecycle"],
                }
            )
        except Exception as exc:
            return self._mutation_error(exc)

    async def _trusted_update_target(self) -> tuple[str, bool]:
        data = await self._request_json()
        if not isinstance(data, dict):
            raise ValueError("INVALID_JSON_PAYLOAD")
        if set(data) not in (
            {"plugin_id", "confirm"},
            {"plugin_id", "confirm", "force"},
        ):
            raise ValueError("CONFIRMATION_REQUIRED")
        if data.get("confirm") is not True:
            raise ValueError("CONFIRMATION_REQUIRED")
        force = data.get("force", False)
        if not isinstance(force, bool):
            raise ValueError("INVALID_FORCE_FLAG")
        plugin_id = data.get("plugin_id")
        if not isinstance(plugin_id, str) or plugin_id not in TRUSTED_BY_ID:
            raise ValueError("PLUGIN_NOT_TRUSTED")
        if plugin_id == PLUGIN_ID:
            raise ValueError("SELF_UPDATE_BLOCKED")
        return plugin_id, force

    async def _set_recommended_enabled(self, enabled: bool):
        try:
            plugin_id = await self._trusted_plugin_id(require_confirmation=not enabled)
            if plugin_id == PLUGIN_ID and not enabled:
                raise ValueError("SELF_DISABLE_BLOCKED")
            snapshot = await self.adapter.set_plugin_enabled(plugin_id, enabled)
            operation = "enable" if enabled else "disable"
            return json_response(
                {
                    "success": True,
                    "plugin_id": plugin_id,
                    "activated": snapshot.activated,
                    "lifecycle": self._lifecycle(operation, snapshot),
                }
            )
        except Exception as exc:
            return self._mutation_error(exc)

    async def _pages_enable(self):
        return await self._set_recommended_enabled(True)

    async def _pages_disable(self):
        return await self._set_recommended_enabled(False)
