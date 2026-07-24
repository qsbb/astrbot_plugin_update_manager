"""AstrBot 非稳定插件管理接口的唯一隔离层。"""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

PLUGIN_INSTALL_SOURCES_KEY = "plugin_install_sources"
SELF_PLUGIN_NAME = "astrbot_plugin_update_manager"


class AdapterUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class CapabilityReport:
    plugin_manager: bool
    list_plugins: bool
    install_sources: bool
    reserved_state: bool
    activated_state: bool
    reload_plugin: bool
    update_plugin: bool
    cron_manager: bool
    cron_add_basic_job: bool
    details: tuple[str, ...] = ()

    @property
    def read_only_ready(self) -> bool:
        return self.list_plugins and self.reserved_state and self.activated_state


@dataclass(frozen=True, slots=True)
class PluginSnapshot:
    name: str
    root_dir_name: str | None
    display_name: str
    version: str
    repo: str
    reserved: bool
    activated: bool
    install_source: Mapping[str, Any] | None


class AstrBotAdapter:
    def __init__(self, context: Any, *, plugin_manager: Any | None = None) -> None:
        self.context = context
        self._plugin_manager = plugin_manager or self._discover_plugin_manager(context)

    @staticmethod
    def _discover_plugin_manager(context: Any) -> Any | None:
        return getattr(context, "plugin_manager", None) or getattr(
            context, "_star_manager", None
        )

    @property
    def plugin_manager(self) -> Any:
        if self._plugin_manager is None:
            raise AdapterUnavailableError("当前 AstrBot 上下文未暴露 PluginManager")
        return self._plugin_manager

    def _getter(self):
        getter = getattr(self.context, "get_all_stars", None)
        if not callable(getter) and self._plugin_manager is not None:
            getter = getattr(
                getattr(self._plugin_manager, "context", None), "get_all_stars", None
            )
        return getter

    def probe_capabilities(self) -> CapabilityReport:
        manager, getter = self._plugin_manager, self._getter()
        stars: Iterable[Any] = ()
        details: list[str] = []
        if callable(getter):
            try:
                stars = tuple(getter())
            except Exception as exc:
                details.append(f"get_all_stars 调用失败: {type(exc).__name__}")
        sample = next(iter(stars), None)
        if sample is None:
            details.append("未加载插件，reserved/activated 仅完成结构性探测")
        cron = getattr(self.context, "cron_manager", None)
        return CapabilityReport(
            manager is not None,
            callable(getter),
            self._can_read_install_sources(),
            sample is None or hasattr(sample, "reserved"),
            sample is None or hasattr(sample, "activated"),
            callable(getattr(manager, "reload", None)),
            callable(getattr(manager, "update_plugin", None)),
            cron is not None,
            callable(getattr(cron, "add_basic_job", None)),
            tuple(details),
        )

    @staticmethod
    def _can_read_install_sources() -> bool:
        try:
            from astrbot.core.utils import shared_preferences as sp  # type: ignore
        except (ImportError, AttributeError):
            return False
        return callable(getattr(sp, "global_get", None))

    def _get_all_stars(self) -> tuple[Any, ...]:
        getter = self._getter()
        if not callable(getter):
            raise AdapterUnavailableError("当前 AstrBot 上下文未暴露 get_all_stars")
        return tuple(getter())

    async def read_install_sources(self) -> dict[str, dict[str, Any]]:
        try:
            from astrbot.core.utils import shared_preferences as sp  # type: ignore
        except (ImportError, AttributeError):
            return {}
        getter = getattr(sp, "global_get", None)
        if not callable(getter):
            return {}
        records = getter(PLUGIN_INSTALL_SOURCES_KEY, {})
        if inspect.isawaitable(records):
            records = await records
        if not isinstance(records, dict):
            return {}
        return {
            str(key): dict(value)
            for key, value in records.items()
            if isinstance(value, dict)
        }

    async def snapshot_plugins(self) -> tuple[PluginSnapshot, ...]:
        sources = await self.read_install_sources()
        result = []
        for star in self._get_all_stars():
            name = str(getattr(star, "name", "") or "").strip()
            root = str(getattr(star, "root_dir_name", "") or "").strip() or None
            result.append(
                PluginSnapshot(
                    name,
                    root,
                    str(getattr(star, "display_name", "") or ""),
                    str(getattr(star, "version", "") or ""),
                    str(getattr(star, "repo", "") or ""),
                    bool(getattr(star, "reserved", False)),
                    bool(getattr(star, "activated", False)),
                    sources.get(root or "") or sources.get(name),
                )
            )
        return tuple(result)

    async def get_plugin(self, plugin_id: str) -> PluginSnapshot | None:
        return next(
            (
                item
                for item in await self.snapshot_plugins()
                if item.name == plugin_id or item.root_dir_name == plugin_id
            ),
            None,
        )

    async def update_plugin(
        self,
        plugin_id: str,
        *,
        source_kind: str,
        source_url: str,
        archive_url: str | None = None,
    ) -> None:
        if plugin_id == SELF_PLUGIN_NAME:
            raise ValueError("SELF_UPDATE_BLOCKED")
        if source_kind not in {"market", "github"} or not source_url:
            raise ValueError("SOURCE_REQUIRED")
        current = await self.get_plugin(plugin_id)
        if current is None or current.reserved:
            raise ValueError("PLUGIN_NOT_MANAGEABLE")
        method = getattr(self.plugin_manager, "update_plugin", None)
        if not callable(method):
            raise AdapterUnavailableError("update_plugin 不可用")
        kwargs = {"plugin_name": plugin_id}
        parameters = inspect.signature(method).parameters
        if "name" in parameters and "plugin_name" not in parameters:
            kwargs = {"name": plugin_id}
        if "download_url" in parameters:
            kwargs["download_url"] = archive_url or source_url
        result = method(**kwargs)
        if inspect.isawaitable(result):
            await result

    async def reload_plugin(self, plugin_id: str) -> None:
        method = getattr(self.plugin_manager, "reload", None)
        if not callable(method):
            raise AdapterUnavailableError("reload 不可用")
        result = method(plugin_id)
        if inspect.isawaitable(result):
            result = await result
        if isinstance(result, tuple) and result and result[0] is False:
            raise RuntimeError("RELOAD_FAILED")

    async def terminate_plugin(self, plugin_id: str) -> None:
        for name in ("terminate_plugin", "unload_plugin", "unload"):
            method = getattr(self.plugin_manager, name, None)
            if callable(method):
                result = method(plugin_id)
                if inspect.isawaitable(result):
                    await result
                return
