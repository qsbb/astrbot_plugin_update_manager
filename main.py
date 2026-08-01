"""凝心溯溪-核：安全、串行、可回滚的 AstrBot 插件自动更新器。"""

from __future__ import annotations

import logging
from functools import partial
from pathlib import Path
from typing import Any

from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register

from .core.adapters.astrbot import AstrBotAdapter
from .core.adapters.registry import (
    DEFAULT_CACHE_TTL_SECONDS,
    DEFAULT_RAW_TIMEOUT_SECONDS,
    CandidateRegistry,
    RegistryError,
    normalize_optional_setting,
)
from .core.adapters.storage import AtomicJsonStore, redact
from .core.catalog import PluginCatalog
from .core.concurrency import bounded_gather
from .core.coordinator import UpdateCoordinator
from .core.diagnostics import diagnose_series
from .core.health import HealthChecker
from .core.mirrors import resolve_mirror
from .core.models import Candidate, FailurePolicy, Policy, UpdatePlan, UpdateRule
from .core.planner import PlanError, UpdatePlanner
from .core.request_context import (
    OWNER_UPDATE_MANAGER,
    PHASE_COMMAND,
    add_reason,
    ensure_context,
    set_artifact,
    set_flag,
)
from .core.scheduler import RuleConflictError, ScheduleService
from .core.transaction import PluginTransaction
from .pages_api import PagesAPIMixin
from .series_diagnostics import (
    diagnostic_clear as clear_diagnostic_events,
    diagnostic_event,
    diagnostic_events as read_diagnostic_events,
    logger,
)

PLUGIN_NAME = "astrbot_plugin_update_manager"
__version__ = "0.8.2"
_current_instance: "UpdateManagerPlugin | None" = None


@register(
    PLUGIN_NAME,
    "凌溪",
    "凝心溯溪-核，安全管理 AstrBot 插件更新、备份、回滚与每日规则",
    __version__,
)
class UpdateManagerPlugin(PagesAPIMixin, Star):
    PLUGIN_HEALTH_CONTRACT = "plugin.health@1.0"

    def __init__(self, context: Context, config: Any = None) -> None:
        super().__init__(context)
        global _current_instance
        _current_instance = self
        self.context, self._config = context, config
        diagnostic_event("plugin.init", "更新管理插件开始初始化")
        self._native_config = config if callable(getattr(config, "save_config", None)) else None
        self._config_overrides: dict[str, Any] = {}
        data_root = self._resolve_data_root()
        self.store = AtomicJsonStore(data_root)
        saved_overrides = self.store.read("manager-config.json", {})
        if isinstance(saved_overrides, dict):
            self._config_overrides = saved_overrides
        self.enabled = self._get_bool("enabled", True)
        self.auto_update_enabled = self._get_bool("auto_update_enabled", False)
        self._terminated = False
        self._apply_log_level(str(self._get("log_level", "INFO")))
        plugin_root = Path(
            str(self._get("plugin_root", "")) or Path(__file__).resolve().parent.parent
        )
        self.adapter = AstrBotAdapter(context)
        self.catalog = PluginCatalog(self.adapter)
        self.planner = UpdatePlanner(
            ttl_seconds=int(self._get("plan_ttl_seconds", 900))
        )
        self.registry = CandidateRegistry(
            timeout_seconds=int(self._get("network_timeout_seconds", 15)),
            cache_ttl_seconds=int(
                self._get("cache_ttl_seconds", DEFAULT_CACHE_TTL_SECONDS)
            ),
            proxy=normalize_optional_setting(self._get("proxy", "")),
            github_token=normalize_optional_setting(self._get("github_token", "")),
            raw_timeout_seconds=float(
                self._get("raw_timeout_seconds", DEFAULT_RAW_TIMEOUT_SECONDS)
            ),
            mirror=resolve_mirror(self._get("github_mirror", "")),
        )
        health = HealthChecker(
            self.adapter,
            stability_seconds=float(self._get("health_stability_seconds", 2.0)),
        )
        self.transaction = PluginTransaction(
            self.adapter,
            health,
            self.store,
            plugin_root=plugin_root,
            backup_root=data_root / "backups",
        )
        self.coordinator = UpdateCoordinator(
            self.catalog, self.planner, self.transaction, self.store
        )
        self.scheduler = ScheduleService(
            getattr(context, "cron_manager", None), self.store, self._scheduled_run
        )
        pages_registered = self._register_pages_web_api()
        interrupted = self.coordinator.recover_interrupted()
        logger.info(
            "[update-manager] v%s loaded; recovered=%d; automatic=%s",
            __version__,
            interrupted,
            self.auto_update_enabled,
        )
        diagnostic_event(
            "plugin.ready",
            "更新管理插件初始化完成",
            details={
                "recovered_count": interrupted,
                "automatic_update_enabled": self.auto_update_enabled,
                "pages_registered": pages_registered,
            },
        )

    def plugin_health(self) -> dict[str, object]:
        checks = {
            "adapter_ready": getattr(self, "adapter", None) is not None,
            "transaction_ready": getattr(self, "transaction", None) is not None,
            "coordinator_ready": getattr(self, "coordinator", None) is not None,
            "runtime_active": not bool(getattr(self, "_terminated", False)),
        }
        reasons = [name.upper() for name, passed in checks.items() if not passed]
        return {
            "status": "ok" if not reasons else "unhealthy",
            "checks": checks,
            "reasons": reasons,
            "version": __version__,
        }

    def diagnostic_log_contract(self) -> dict[str, object]:
        return {
            "name": "series.diagnostics",
            "version": "1.0",
            "plugin": PLUGIN_NAME,
            "capabilities": ("read", "clear", "aggregate"),
            "storage": "memory_only",
            "astrbot_log_propagation": False,
        }

    def diagnostic_events(self, after_seq: int = 0, limit: int = 200) -> dict[str, Any]:
        return read_diagnostic_events(after_seq=after_seq, limit=limit)

    def diagnostic_clear(self) -> None:
        clear_diagnostic_events()

    def _get(self, key: str, default: Any) -> Any:
        if key in self._config_overrides:
            return self._config_overrides[key]
        if isinstance(self._config, dict):
            return self._config.get(key, default)
        getter = getattr(self._config, "get", None)
        if callable(getter):
            try:
                return getter(key, default)
            except TypeError:
                value = getter(key)
                return default if value is None else value
        return default

    def _get_bool(self, key: str, default: bool) -> bool:
        value = self._get(key, default)
        return (
            value.strip().lower() in {"1", "true", "yes", "on"}
            if isinstance(value, str)
            else bool(value)
        )

    def _resolve_data_root(self) -> Path:
        configured = str(self._get("data_dir", "")).strip()
        if configured:
            return Path(configured) / PLUGIN_NAME
        getter = getattr(self.context, "get_plugin_data_dir", None)
        if callable(getter):
            try:
                return Path(getter(PLUGIN_NAME))
            except TypeError:
                return Path(getter())
        return Path.cwd() / "data" / "plugin_data" / PLUGIN_NAME

    @staticmethod
    def _apply_log_level(level_name: str) -> None:
        level = getattr(logging, level_name.upper(), None)
        underlying = (
            logger
            if callable(getattr(logger, "setLevel", None))
            else getattr(logger, "_logger", None) or getattr(logger, "logger", None)
        )
        if (
            isinstance(level, int)
            and underlying is not None
            and callable(getattr(underlying, "setLevel", None))
        ):
            underlying.setLevel(level)

    async def initialize(self) -> None:
        """插件激活后恢复唯一 runtime job；配置关闭时不注册调度。"""
        if not self.enabled:
            return
        try:
            if self.auto_update_enabled:
                await self.scheduler.rebuild()
            else:
                await self.scheduler.remove_job()
            self.transaction.cleanup(
                keep_success=max(1, int(self._get("backup_keep_success", 3))),
                failed_days=max(0, int(self._get("backup_failed_days", 7))),
                capacity_bytes=max(1, int(self._get("backup_capacity_mb", 2048)))
                * 1024**2,
            )
        except Exception as exc:
            logger.error("[update-manager] initialize failed: %s", type(exc).__name__)

    def _disabled_notice(self) -> str | None:
        """插件被配置为禁用时，返回统一提示；否则返回 None。"""
        if self.enabled:
            return None
        return "凝心溯溪-核 已被配置禁用（enabled=false）：管理命令与调度均不执行。"

    @filter.command_group("aup")
    def aup_group(self) -> None:
        """自动更新管理员命令。"""

    @filter.permission_type(filter.PermissionType.ADMIN)
    @aup_group.command("probe")
    async def aup_probe(self, event: AstrMessageEvent):
        notice = self._disabled_notice()
        if notice:
            yield event.plain_result(notice)
            return
        report = self.adapter.probe_capabilities()
        lines = [
            "凝心溯溪-核 / 能力探针",
            f"PluginManager: {self._yn(report.plugin_manager)}",
            f"插件目录: {self._yn(report.list_plugins)}",
            f"安装来源: {self._yn(report.install_sources)}",
            f"安装接口: {self._yn(report.install_plugin)}",
            f"更新接口: {self._yn(report.update_plugin)}",
            f"启用接口: {self._yn(report.turn_on_plugin)}",
            f"停用接口: {self._yn(report.turn_off_plugin)}",
            f"重载接口: {self._yn(report.reload_plugin)}",
            f"定时任务: {self._yn(report.cron_add_basic_job)}",
        ]
        lines.extend(f"备注: {item}" for item in report.details)
        yield event.plain_result("\n".join(lines))

    @filter.permission_type(filter.PermissionType.ADMIN)
    @aup_group.command("catalog")
    async def aup_catalog(self, event: AstrMessageEvent):
        notice = self._disabled_notice()
        if notice:
            yield event.plain_result(notice)
            return
        items = await self.catalog.scan()
        lines = [f"插件目录（{len(items)} 项）"]
        for item in items:
            status = "可规划" if item.eligible else "阻断:" + ",".join(item.reasons)
            lines.append(
                f"- {item.plugin_id} {item.current_version or '<unknown>'} [{status}]"
            )
        yield event.plain_result("\n".join(lines))

    async def _candidates(self, selected: tuple[str, ...]) -> dict[str, Candidate]:
        """并发（有上限）解析候选；单个仓库慢不再线性拖长整批检查。"""
        items = {item.plugin_id: item for item in await self.catalog.scan()}
        snapshots = {
            (item.name or item.root_dir_name or ""): item
            for item in await self.adapter.snapshot_plugins()
        }
        candidates: dict[str, Candidate] = {}
        remote: list[tuple[str, Any]] = []
        for plugin_id in dict.fromkeys(selected):
            item = items.get(plugin_id)
            if item and item.source_kind == "github" and item.source_url:
                remote.append(
                    (
                        plugin_id,
                        partial(
                            self.registry.github_latest,
                            plugin_id,
                            item.current_version,
                            item.source_url,
                        ),
                    )
                )
            elif item and item.source_kind == "market" and item.source_url:
                record = snapshots.get(plugin_id)
                candidates[plugin_id] = self.registry.market_candidate(
                    plugin_id,
                    item.current_version,
                    item.source_url,
                    dict(record.install_source or {}) if record else {},
                )
        if remote:
            resolved = await bounded_gather(
                [factory for _, factory in remote],
                limit=self._version_check_concurrency(),
            )
            for (plugin_id, _), candidate in zip(remote, resolved):
                candidates[plugin_id] = candidate
        return candidates

    @filter.permission_type(filter.PermissionType.ADMIN)
    @aup_group.command("plan")
    async def aup_plan(
        self, event: AstrMessageEvent, plugins: str, policy: str = "stable"
    ):
        """冻结计划：plugins 为逗号分隔的显式插件 ID。"""
        notice = self._disabled_notice()
        if notice:
            yield event.plain_result(notice)
            return
        try:
            selected = self._parse_ids(plugins)
            rule = self.scheduler.load()
            catalog = await self.catalog.scan()
            plan = self.planner.create(
                catalog,
                await self._candidates(selected),
                selected=selected,
                astrbot_version=self._astrbot_version(),
                policy=Policy(policy),
                rule_revision=rule.revision,
                minimum_release_age_hours=rule.minimum_release_age_hours,
            )
            self.store.write(f"plan-{plan.plan_id}.json", plan.to_dict())
            yield event.plain_result(
                f"计划已冻结: {plan.plan_id}\n哈希: {plan.plan_hash}\n项目: {len(plan.items)}\n有效至: {plan.expires_at}"
            )
        except (ValueError, PlanError, RegistryError) as exc:
            yield event.plain_result(f"计划失败: {redact(exc)}")

    @filter.permission_type(filter.PermissionType.ADMIN)
    @aup_group.command("run")
    async def aup_run(self, event: AstrMessageEvent, plan_id: str):
        """执行已冻结计划；同一计划不可重放。"""
        notice = self._disabled_notice()
        if notice:
            yield event.plain_result(notice)
            return
        try:
            plan = self._load_plan(plan_id)
            rule = self.scheduler.load()
            run = await self.coordinator.execute(
                plan,
                astrbot_version=self._astrbot_version(),
                rule_revision=rule.revision,
            )
            self.transaction.cleanup(
                keep_success=max(1, int(self._get("backup_keep_success", 3))),
                failed_days=max(0, int(self._get("backup_failed_days", 7))),
                capacity_bytes=max(1, int(self._get("backup_capacity_mb", 2048)))
                * 1024**2,
            )
            yield event.plain_result(self._run_summary(run))
        except Exception as exc:
            yield event.plain_result(
                f"执行失败: {type(exc).__name__}: {redact(exc)}"
            )

    @filter.permission_type(filter.PermissionType.ADMIN)
    @aup_group.command("rule")
    async def aup_rule(
        self,
        event: AstrMessageEvent,
        action: str = "show",
        plugins: str = "",
        local_time: str = "04:30",
        timezone_name: str = "Asia/Shanghai",
        policy: str = "check_only",
    ):
        notice = self._disabled_notice()
        if notice:
            yield event.plain_result(notice)
            return
        try:
            current = self.scheduler.load()
            if action == "show":
                next_run = self.scheduler.next_run(current)
                yield event.plain_result(
                    f"规则 revision={current.revision} enabled={current.enabled} plugins={','.join(current.plugin_ids) or '-'} next={next_run or '-'}"
                )
                return
            if action not in {"enable", "disable"}:
                raise ValueError("action 仅支持 show/enable/disable")
            enabled = action == "enable"
            if enabled and not self.auto_update_enabled:
                raise ValueError("配置 auto_update_enabled=false，拒绝启用写入规则")
            updated = UpdateRule(
                enabled=enabled,
                plugin_ids=self._parse_ids(plugins) if enabled else current.plugin_ids,
                local_time=local_time,
                timezone=timezone_name,
                policy=Policy(policy).value,
                revision=current.revision,
            )
            saved = self.scheduler.save(updated, expected_revision=current.revision)
            await self.scheduler.rebuild()
            yield event.plain_result(
                f"规则已保存 revision={saved.revision} next={self.scheduler.next_run(saved) or '-'}"
            )
        except (ValueError, RuleConflictError) as exc:
            yield event.plain_result(f"规则失败: {exc}")

    @filter.permission_type(filter.PermissionType.ADMIN)
    @aup_group.command("dryrun")
    async def aup_dryrun(
        self, event: AstrMessageEvent, plugins: str, policy: str = "stable"
    ):
        """预演候选与资格，不保存计划且不修改插件。"""
        notice = self._disabled_notice()
        if notice:
            yield event.plain_result(notice)
            return
        try:
            selected = self._parse_ids(plugins)
            rule = self.scheduler.load()
            plan = self.planner.create(
                await self.catalog.scan(),
                await self._candidates(selected),
                selected=selected,
                astrbot_version=self._astrbot_version(),
                policy=Policy(policy),
                rule_revision=rule.revision,
                minimum_release_age_hours=rule.minimum_release_age_hours,
            )
            lines = [f"预演通过（{len(plan.items)} 项，不会修改文件）"]
            lines.extend(
                f"- {item.plugin_id}: {item.from_version} -> {item.to_version}"
                for item in plan.items
            )
            yield event.plain_result("\n".join(lines))
        except (ValueError, PlanError, RegistryError) as exc:
            yield event.plain_result(f"预演失败: {redact(exc)}")

    @filter.permission_type(filter.PermissionType.ADMIN)
    @aup_group.command("rollback")
    async def aup_rollback(self, event: AstrMessageEvent, tx_id: str):
        """人工回滚一个仍满足版本前置条件的已提交事务。"""
        notice = self._disabled_notice()
        if notice:
            yield event.plain_result(notice)
            return
        try:
            result = await self.coordinator.manual_rollback(tx_id)
            yield event.plain_result(
                f"人工回滚 {result.get('original_tx_id', tx_id)}: {result['state']}"
            )
        except Exception as exc:
            yield event.plain_result(
                f"人工回滚失败: {type(exc).__name__}: {redact(exc)}"
            )

    @filter.permission_type(filter.PermissionType.ADMIN)
    @aup_group.command("cancel")
    async def aup_cancel(self, event: AstrMessageEvent):
        """在当前插件事务结束后停止批次后续项目。"""
        notice = self._disabled_notice()
        if notice:
            yield event.plain_result(notice)
            return
        self.coordinator.cancel()
        yield event.plain_result("已请求在当前插件事务边界停止批次。")

    @filter.permission_type(filter.PermissionType.ADMIN)
    @aup_group.command("status")
    async def aup_status(self, event: AstrMessageEvent):
        notice = self._disabled_notice()
        if notice:
            yield event.plain_result(notice)
            return
        runs = sorted(
            self.store.root.glob("run-*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not runs:
            yield event.plain_result("暂无执行记录。")
            return
        yield event.plain_result(self._run_summary(self.store.read(runs[0].name, {})))

    @filter.permission_type(filter.PermissionType.ADMIN)
    @aup_group.command("diag")
    async def aup_diag(self, event: AstrMessageEvent):
        """诊断知、言、序、情、境、声、核七个系列插件。"""
        report = await diagnose_series(self.adapter)
        request_context = ensure_context(event, PHASE_COMMAND)
        set_artifact(
            request_context,
            OWNER_UPDATE_MANAGER,
            "suite_diagnostics",
            report,
        )
        set_flag(
            request_context,
            OWNER_UPDATE_MANAGER,
            "suite_healthy",
            report["status"] == "ok",
        )
        add_reason(
            request_context,
            OWNER_UPDATE_MANAGER,
            "SUITE_DIAGNOSTICS_COMPLETED",
        )
        lines = [
            f"凝心溯溪套件诊断: {report['healthy']}/{report['total']} 正常",
        ]
        status_names = {
            "ok": "正常",
            "compatible": "兼容模式",
            "degraded": "降级",
            "unhealthy": "异常",
            "missing": "缺失",
        }
        for row in report["members"]:
            version = f" v{row['version']}" if row["version"] else ""
            lines.append(
                f"- {row['label']}{version}: "
                f"{status_names.get(row['status'], row['status'])} ({row['reason']})"
            )
        yield event.plain_result("\n".join(lines))

    async def _scheduled_run(self, rule: UpdateRule) -> None:
        if self.coordinator.busy:
            self.store.append_audit(
                {
                    "event": "scheduled_check",
                    "revision": rule.revision,
                    "result": "SKIPPED_BUSY",
                }
            )
            return
        if not self.auto_update_enabled or rule.policy == Policy.CHECK_ONLY.value:
            self.store.append_audit(
                {
                    "event": "scheduled_check",
                    "revision": rule.revision,
                    "result": "CHECK_ONLY",
                }
            )
            return
        catalog = await self.catalog.scan()
        candidates = await self._candidates(rule.plugin_ids)
        plan = self.planner.create(
            catalog,
            candidates,
            selected=rule.plugin_ids,
            astrbot_version=self._astrbot_version(),
            policy=Policy(rule.policy),
            rule_revision=rule.revision,
            prerelease=rule.prerelease,
            minimum_release_age_hours=rule.minimum_release_age_hours,
        )
        await self.coordinator.execute(
            plan,
            astrbot_version=self._astrbot_version(),
            rule_revision=rule.revision,
            on_failure=FailurePolicy(rule.on_failure),
            trigger="schedule",
        )
        self.transaction.cleanup(
            keep_success=max(1, int(self._get("backup_keep_success", 3))),
            failed_days=max(0, int(self._get("backup_failed_days", 7))),
            capacity_bytes=max(1, int(self._get("backup_capacity_mb", 2048)))
            * 1024**2,
        )

    def _astrbot_version(self) -> str:
        value = getattr(self.context, "version", None) or getattr(
            self.context, "astrbot_version", None
        )
        if not value:
            raise RuntimeError("ASTRBOT_VERSION_UNAVAILABLE")
        return str(value)

    @staticmethod
    def _parse_ids(value: str) -> tuple[str, ...]:
        ids = tuple(
            dict.fromkeys(item.strip() for item in value.split(",") if item.strip())
        )
        if not ids or any(
            len(item) > 128
            or any(
                char
                not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
                for char in item
            )
            for item in ids
        ):
            raise ValueError("插件 ID 必须是非空逗号分隔的字母、数字、下划线或连字符")
        return ids

    def _load_plan(self, plan_id: str) -> UpdatePlan:
        if (
            not plan_id
            or len(plan_id) > 64
            or any(char not in "0123456789abcdef-" for char in plan_id.lower())
        ):
            raise ValueError("非法计划 ID")
        raw = self.store.read(f"plan-{plan_id}.json", None)
        if raw is None:
            raise ValueError("计划不存在")
        return UpdatePlan.from_dict(raw)

    @staticmethod
    def _run_summary(run: dict) -> str:
        results = run.get("results", [])
        return f"批次 {run.get('run_id', '<unknown>')}：" + (
            ", ".join(
                f"{item.get('plugin_id')}={item.get('state')}" for item in results
            )
            or "尚无结果"
        )

    @staticmethod
    def _yn(value: bool) -> str:
        return "可用" if value else "不可用"

    async def terminate(self) -> None:
        global _current_instance
        self.coordinator.cancel()
        try:
            await self.scheduler.close()
        finally:
            try:
                await self.registry.close()
            finally:
                self.adapter = None  # type: ignore[assignment]
                self._terminated = True
                if _current_instance is self:
                    _current_instance = None
        diagnostic_event("plugin.terminated", "更新管理插件已卸载")
        logger.info("[update-manager] terminated")
