"""AstrBot 非稳定插件管理接口的唯一隔离层。"""

from __future__ import annotations

import asyncio
import inspect
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

import yaml
from packaging.version import InvalidVersion, Version

PLUGIN_INSTALL_SOURCES_KEY = "plugin_install_sources"
SELF_PLUGIN_NAME = "astrbot_plugin_update_manager"


class AdapterUnavailableError(RuntimeError):
    pass


def resolve_display_name(
    candidates: Iterable[Any], plugin_id: str, *, fallback: bool = True
) -> str:
    """按优先级取第一个真正的展示名，并过滤复读的插件标识符。"""
    for candidate in candidates:
        name = str(candidate or "").strip()
        if name and name != plugin_id:
            return name
    return plugin_id if fallback else ""


@dataclass(frozen=True, slots=True)
class CapabilityReport:
    plugin_manager: bool
    list_plugins: bool
    install_sources: bool
    reserved_state: bool
    activated_state: bool
    reload_plugin: bool
    install_plugin: bool
    update_plugin: bool
    turn_on_plugin: bool
    turn_off_plugin: bool
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
    loaded: bool
    metadata_complete: bool
    install_source: Mapping[str, Any] | None


@dataclass(frozen=True, slots=True)
class DiscoveryReport:
    runtime_count: int
    discovered_count: int
    roots_checked: int
    diagnostics: tuple[str, ...] = ()


class AstrBotAdapter:
    def __init__(self, context: Any, *, plugin_manager: Any | None = None) -> None:
        self.context = context
        self._plugin_manager = plugin_manager or self._discover_plugin_manager(context)
        self._mutation_lock = asyncio.Lock()
        self.last_discovery_report = DiscoveryReport(0, 0, 0, ("NOT_SCANNED",))

    @staticmethod
    def _discover_plugin_manager(context: Any) -> Any | None:
        # AstrBot 4.x exposes the manager as Context._star_manager.  Some
        # integrations expose the public alias instead, so accept both without
        # depending on a private field name alone.
        for attribute in ("plugin_manager", "star_manager", "_star_manager"):
            manager = getattr(context, attribute, None)
            if manager is not None:
                return manager
        return None

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
            callable(getattr(manager, "install_plugin", None)),
            callable(getattr(manager, "update_plugin", None)),
            callable(getattr(manager, "turn_on_plugin", None)),
            callable(getattr(manager, "turn_off_plugin", None)),
            cron is not None,
            callable(getattr(cron, "add_basic_job", None)),
            tuple(details),
        )

    @staticmethod
    def _shared_preferences() -> Any | None:
        """Return AstrBot's SharedPreferences instance across 4.x layouts."""
        try:
            from astrbot.core import sp  # type: ignore
        except (ImportError, AttributeError):
            sp = None
        if callable(getattr(sp, "global_get", None)):
            return sp
        try:
            from astrbot.core.utils import shared_preferences as module  # type: ignore
        except (ImportError, AttributeError):
            return None
        return module if callable(getattr(module, "global_get", None)) else None

    @classmethod
    def _can_read_install_sources(cls) -> bool:
        return cls._shared_preferences() is not None

    def _get_all_stars(self) -> tuple[Any, ...]:
        getter = self._getter()
        if not callable(getter):
            raise AdapterUnavailableError("当前 AstrBot 上下文未暴露 get_all_stars")
        return tuple(getter())

    async def read_install_sources(self) -> dict[str, dict[str, Any]]:
        sp = self._shared_preferences()
        if sp is None:
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

    @staticmethod
    def _contained(path: Path, root: Path) -> bool:
        try:
            path.relative_to(root)
        except ValueError:
            return False
        return True

    def _discovery_roots(self) -> tuple[tuple[Path, bool], ...]:
        manager = self._plugin_manager
        if manager is None:
            return ()
        roots = []
        for attribute, reserved in (
            ("plugin_store_path", False),
            ("plugin_path", False),
            ("reserved_plugin_path", True),
        ):
            raw = getattr(manager, attribute, None)
            if not isinstance(raw, (str, Path)) or not str(raw).strip():
                continue
            root = Path(raw).expanduser().resolve()
            if root not in {item[0] for item in roots}:
                roots.append((root, reserved))
        return tuple(roots)

    @staticmethod
    def _read_metadata(path: Path) -> Mapping[str, Any] | None:
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, yaml.YAMLError):
            return None
        return data if isinstance(data, Mapping) else None

    @staticmethod
    def _module_records(records: Any) -> Iterable[Any]:
        if isinstance(records, Mapping):
            if any(key in records for key in ("module_path", "path", "pname")):
                return (records,)
            return records.values()
        if isinstance(records, Iterable) and not isinstance(records, (str, bytes, Path)):
            return records
        return (records,)

    def _module_plugin_dir(self, record: Any, root: Path) -> Path | None:
        if isinstance(record, Mapping):
            raw_name = record.get("pname") or record.get("root_dir_name")
            raw_path = record.get("module_path") or record.get("path")
        elif isinstance(record, (tuple, list)):
            raw_name = record[0] if record and isinstance(record[0], str) else None
            raw_path = next(
                (
                    value
                    for value in reversed(record)
                    if isinstance(value, Path)
                    or (isinstance(value, str) and ("/" in value or "\\" in value))
                ),
                None,
            )
        else:
            raw_name = getattr(record, "pname", None) or getattr(
                record, "root_dir_name", None
            )
            raw_path = (
                getattr(record, "module_path", None)
                or getattr(record, "path", None)
                or getattr(record, "__file__", None)
            )
            if raw_path is None and isinstance(record, (str, Path)):
                raw_path = record
        if isinstance(raw_path, (str, Path)):
            module_path = Path(raw_path).expanduser().resolve()
            plugin_dir = module_path if module_path.is_dir() else module_path.parent
            if self._contained(plugin_dir, root):
                return plugin_dir
        if isinstance(raw_name, str) and raw_name.strip():
            named_dir = (root / raw_name.strip()).resolve()
            if self._contained(named_dir, root):
                return named_dir
        return None

    def _discoverable_directories(
        self, root: Path, diagnostics: list[str]
    ) -> tuple[Path, ...]:
        candidates = []
        getter = getattr(self._plugin_manager, "_get_plugin_modules", None)
        if callable(getter):
            try:
                records = getter()
                candidates.extend(
                    plugin_dir
                    for record in self._module_records(records)
                    if (plugin_dir := self._module_plugin_dir(record, root)) is not None
                )
            except Exception:
                diagnostics.append("DISCOVERY_MODULES_UNAVAILABLE")
        try:
            candidates.extend(root.iterdir())
        except OSError:
            diagnostics.append("DISCOVERY_ROOT_UNREADABLE")
        return tuple(dict.fromkeys(candidates))

    def _discover_snapshots(
        self, sources: Mapping[str, Mapping[str, Any]]
    ) -> tuple[PluginSnapshot, ...]:
        result = []
        diagnostics: list[str] = []
        roots = self._discovery_roots()
        for root, reserved in roots:
            if not root.is_dir():
                diagnostics.append("DISCOVERY_ROOT_UNAVAILABLE")
                continue
            children = self._discoverable_directories(root, diagnostics)
            for child in children:
                try:
                    resolved = child.resolve()
                except OSError:
                    diagnostics.append("DISCOVERY_PATH_UNRESOLVED")
                    continue
                if child.is_symlink() or not child.is_dir() or not self._contained(resolved, root):
                    if child.is_symlink():
                        diagnostics.append("DISCOVERY_PATH_BLOCKED")
                    continue
                root_name = child.name
                metadata_path = resolved / "metadata.yaml"
                if not metadata_path.is_file() or not self._contained(
                    metadata_path.resolve(), root
                ):
                    continue
                metadata = self._read_metadata(metadata_path)
                if metadata is None:
                    diagnostics.append("METADATA_UNREADABLE")
                    continue
                name = str(metadata.get("name") or "").strip()
                version = str(metadata.get("version") or "").strip()
                repo = str(metadata.get("repo") or metadata.get("source_url") or "").strip()
                install_source = dict(sources.get(root_name) or sources.get(name) or {})
                for key in ("install_method", "source", "source_kind", "url", "source_url"):
                    if key in metadata and metadata[key] is not None:
                        install_source.setdefault(key, metadata[key])
                if repo:
                    install_source.setdefault("repo", repo)
                complete = bool(name and version)
                result.append(
                    PluginSnapshot(
                        name=name or root_name,
                        root_dir_name=root_name,
                        display_name=resolve_display_name(
                            (metadata.get("display_name"),),
                            name or root_name,
                            fallback=False,
                        ),
                        version=version,
                        repo=repo,
                        reserved=reserved,
                        activated=False,
                        loaded=False,
                        metadata_complete=complete,
                        install_source=install_source or None,
                    )
                )
        self.last_discovery_report = DiscoveryReport(
            runtime_count=0,
            discovered_count=len(result),
            roots_checked=len(roots),
            diagnostics=tuple(sorted(set(diagnostics))),
        )
        return tuple(result)

    @staticmethod
    def _valid_version(value: str) -> bool:
        try:
            Version(value.strip())
        except (InvalidVersion, AttributeError):
            return False
        return True

    @classmethod
    def _merge_snapshot_pair(
        cls, runtime: PluginSnapshot, discovered: PluginSnapshot
    ) -> PluginSnapshot:
        version = runtime.version.strip()
        if not cls._valid_version(version) and cls._valid_version(discovered.version):
            version = discovered.version
        # 运行时已加载的身份是权威的：覆盖它会让后续按 root/name 去重失配，
        # 从而把同一个插件在目录页里显示成两行。
        plugin_id = runtime.name or discovered.name
        return PluginSnapshot(
            name=plugin_id,
            root_dir_name=runtime.root_dir_name or discovered.root_dir_name,
            display_name=resolve_display_name(
                (discovered.display_name, runtime.display_name),
                plugin_id,
                fallback=False,
            ),
            version=version,
            repo=runtime.repo or discovered.repo,
            reserved=runtime.reserved,
            activated=runtime.activated,
            loaded=True,
            metadata_complete=runtime.metadata_complete or discovered.metadata_complete,
            install_source=runtime.install_source or discovered.install_source,
        )

    @classmethod
    def _merge_snapshots(
        cls,
        runtime: Iterable[PluginSnapshot],
        discovered: Iterable[PluginSnapshot],
    ) -> tuple[PluginSnapshot, ...]:
        merged = list(runtime)
        metadata_merged: set[int] = set()
        for candidate in discovered:
            matched_by_root = False
            duplicate_index = next(
                (
                    index
                    for index, item in enumerate(merged)
                    if candidate.root_dir_name
                    and item.root_dir_name == candidate.root_dir_name
                ),
                None,
            )
            if duplicate_index is not None:
                matched_by_root = True
            if duplicate_index is None and candidate.name:
                duplicate_index = next(
                    (
                        index
                        for index, item in enumerate(merged)
                        if item.name == candidate.name
                    ),
                    None,
                )
            if duplicate_index is None:
                merged.append(candidate)
            elif merged[duplicate_index].loaded and (
                matched_by_root or duplicate_index not in metadata_merged
            ):
                merged[duplicate_index] = cls._merge_snapshot_pair(
                    merged[duplicate_index], candidate
                )
                metadata_merged.add(duplicate_index)
        return tuple(merged)

    async def snapshot_plugins(self) -> tuple[PluginSnapshot, ...]:
        sources = await self.read_install_sources()
        runtime = []
        runtime_diagnostics: list[str] = []
        try:
            stars = self._get_all_stars()
        except AdapterUnavailableError:
            stars = ()
            runtime_diagnostics.append("RUNTIME_LIST_UNAVAILABLE")
        except Exception as exc:
            stars = ()
            runtime_diagnostics.append(f"RUNTIME_LIST_FAILED:{type(exc).__name__}")
        for star in stars:
            name = str(getattr(star, "name", "") or "").strip()
            root = str(getattr(star, "root_dir_name", "") or "").strip() or None
            runtime.append(
                PluginSnapshot(
                    name=name,
                    root_dir_name=root,
                    display_name=resolve_display_name(
                        (getattr(star, "display_name", ""),),
                        name or root or "",
                        fallback=False,
                    ),
                    version=str(getattr(star, "version", "") or ""),
                    repo=str(getattr(star, "repo", "") or ""),
                    reserved=bool(getattr(star, "reserved", False)),
                    activated=bool(getattr(star, "activated", False)),
                    loaded=True,
                    metadata_complete=bool(name and root),
                    install_source=sources.get(root or "") or sources.get(name),
                )
            )
        discovered = self._discover_snapshots(sources)
        discovery_report = self.last_discovery_report
        merged = self._merge_snapshots(runtime, discovered)
        self.last_discovery_report = DiscoveryReport(
            runtime_count=len(runtime),
            discovered_count=sum(not item.loaded for item in merged),
            roots_checked=discovery_report.roots_checked,
            diagnostics=tuple(
                sorted(set(discovery_report.diagnostics + tuple(runtime_diagnostics)))
            ),
        )
        return merged

    async def get_plugin(self, plugin_id: str) -> PluginSnapshot | None:
        return next(
            (
                item
                for item in await self.snapshot_plugins()
                if item.name == plugin_id or item.root_dir_name == plugin_id
            ),
            None,
        )

    async def get_plugin_instance(self, plugin_id: str) -> Any | None:
        """Best-effort 获取运行中实例，仅供只读健康探针使用。"""
        getter = getattr(self.context, "get_star_instance", None)
        if callable(getter):
            try:
                instance = getter(plugin_id)
                if inspect.isawaitable(instance):
                    instance = await instance
                if instance is not None:
                    return instance
            except Exception:
                pass
        try:
            stars = self._get_all_stars()
        except Exception:
            return None
        for star in stars:
            identities = {
                str(getattr(star, "name", "") or ""),
                str(getattr(star, "root_dir_name", "") or ""),
            }
            if plugin_id not in identities:
                continue
            if callable(getattr(star, "plugin_health", None)):
                return star
            for attribute in ("star", "instance", "star_instance", "plugin"):
                instance = getattr(star, attribute, None)
                if instance is not None:
                    return instance
        return None

    @staticmethod
    def _validate_result(result: Any, operation: str) -> None:
        if result is False:
            raise RuntimeError(f"{operation.upper()}_FAILED")
        if isinstance(result, tuple) and result and result[0] is False:
            raise RuntimeError(f"{operation.upper()}_FAILED")
        if isinstance(result, Mapping) and result.get("success") is False:
            raise RuntimeError(f"{operation.upper()}_FAILED")

    @staticmethod
    def _parameters(method: Any) -> Mapping[str, inspect.Parameter]:
        try:
            return inspect.signature(method).parameters
        except (TypeError, ValueError) as exc:
            raise AdapterUnavailableError("无法探测插件管理接口签名") from exc

    @classmethod
    def _identity_kwargs(cls, method: Any, plugin_id: str) -> dict[str, Any]:
        parameters = cls._parameters(method)
        for key in ("plugin_name", "name", "plugin_id", "pname"):
            if key in parameters:
                return {key: plugin_id}
        raise AdapterUnavailableError("插件管理接口缺少可识别的插件 ID 参数")

    async def _invoke(self, operation: str, plugin_id: str, **extra: Any) -> Any:
        method = getattr(self.plugin_manager, operation, None)
        if not callable(method):
            raise AdapterUnavailableError(f"{operation} 不可用")
        kwargs = self._identity_kwargs(method, plugin_id)
        parameters = self._parameters(method)
        accepts_kwargs = any(
            parameter.kind is inspect.Parameter.VAR_KEYWORD
            for parameter in parameters.values()
        )
        kwargs.update(
            {
                key: value
                for key, value in extra.items()
                if key in parameters or accepts_kwargs
            }
        )
        result = method(**kwargs)
        if inspect.isawaitable(result):
            result = await result
        self._validate_result(result, operation)
        return result

    async def install_plugin(self, plugin_id: str, *, repo_url: str) -> PluginSnapshot:
        if not repo_url:
            raise ValueError("SOURCE_REQUIRED")
        async with self._mutation_lock:
            if await self.get_plugin(plugin_id) is not None:
                raise ValueError("PLUGIN_ALREADY_INSTALLED")
            method = getattr(self.plugin_manager, "install_plugin", None)
            if not callable(method):
                raise AdapterUnavailableError("install_plugin 不可用")
            parameters = self._parameters(method)
            source_key = next(
                (
                    key
                    for key in ("repo_url", "source_url", "plugin_url", "url", "repo")
                    if key in parameters
                ),
                None,
            )
            if source_key is None:
                raise AdapterUnavailableError("install_plugin 不支持可信仓库 URL 参数")
            kwargs = {source_key: repo_url}
            result = method(**kwargs)
            if inspect.isawaitable(result):
                result = await result
            self._validate_result(result, "install_plugin")
            installed = await self.get_plugin(plugin_id)
            if installed is None or not installed.loaded:
                raise RuntimeError("INSTALL_RESULT_NOT_FOUND")
            return installed

    async def update_plugin(
        self,
        plugin_id: str,
        *,
        source_kind: str,
        source_url: str,
        archive_url: str | None = None,
    ) -> PluginSnapshot:
        if plugin_id == SELF_PLUGIN_NAME:
            raise ValueError("SELF_UPDATE_BLOCKED")
        if source_kind not in {"market", "github"} or not source_url:
            raise ValueError("SOURCE_REQUIRED")
        async with self._mutation_lock:
            current = await self.get_plugin(plugin_id)
            if current is None or current.reserved or not current.loaded:
                raise ValueError("PLUGIN_NOT_MANAGEABLE")
            method = getattr(self.plugin_manager, "update_plugin", None)
            if not callable(method):
                raise AdapterUnavailableError("update_plugin 不可用")
            parameters = self._parameters(method)
            extra: dict[str, Any] = {}
            archive_key = next(
                (key for key in ("download_url", "archive_url") if key in parameters),
                None,
            )
            accepts_kwargs = any(
                parameter.kind is inspect.Parameter.VAR_KEYWORD
                for parameter in parameters.values()
            )
            if archive_key or accepts_kwargs:
                archive_key = archive_key or "download_url"
                parameter = parameters.get(archive_key)
                if archive_url:
                    extra[archive_key] = archive_url
                elif parameter and parameter.default is inspect.Parameter.empty:
                    raise ValueError("ARCHIVE_URL_REQUIRED")
            await self._invoke("update_plugin", plugin_id, **extra)
            updated = await self.get_plugin(plugin_id)
            if updated is None or not updated.loaded:
                raise RuntimeError("UPDATE_RESULT_NOT_FOUND")
            return updated

    async def set_plugin_enabled(self, plugin_id: str, enabled: bool) -> PluginSnapshot:
        if plugin_id == SELF_PLUGIN_NAME and not enabled:
            raise ValueError("SELF_DISABLE_BLOCKED")
        operation = "turn_on_plugin" if enabled else "turn_off_plugin"
        async with self._mutation_lock:
            current = await self.get_plugin(plugin_id)
            if current is None or current.reserved or not current.loaded:
                raise ValueError("PLUGIN_NOT_MANAGEABLE")
            await self._invoke(operation, plugin_id)
            updated = await self.get_plugin(plugin_id)
            if updated is None or updated.activated is not enabled:
                raise RuntimeError("ACTIVATION_RESULT_MISMATCH")
            return updated

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
