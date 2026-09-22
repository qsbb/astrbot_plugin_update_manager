"""自动备份的调度：独立开关 / 独立时间 / 独立时区，与每日更新规则互不影响。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Callable
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .models import utc_now
from .scheduler import remove_named_cron_jobs

#: cron 任务名（与更新规则的 JOB_ID 区分）
JOB_ID = "astrbot_plugin_update_manager_backup"

INVALID_TIMEZONE_OR_TIME = "INVALID_TIMEZONE_OR_TIME"
CRON_UNAVAILABLE = "CRON_UNAVAILABLE"

DEFAULT_LOCAL_TIME = "03:30"
DEFAULT_TIMEZONE = "Asia/Shanghai"


class BackupScheduleError(ValueError):
    """备份计划校验失败（时间或时区不合法 / cron 不可用）。"""


def _coerce_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"1", "true", "yes", "on"}:
            return True
        if text in {"0", "false", "no", "off", ""}:
            return False
    if value is None:
        return default
    return bool(value)


@dataclass(frozen=True, slots=True)
class BackupSettings:
    enabled: bool = False
    local_time: str = DEFAULT_LOCAL_TIME
    timezone: str = DEFAULT_TIMEZONE

    @classmethod
    def from_config(cls, getter: Callable[..., Any]) -> "BackupSettings":
        """从核配置读取（``getter(key, default)``）。"""
        raw_time = str(getter("auto_backup_local_time", DEFAULT_LOCAL_TIME) or "").strip()
        raw_zone = str(getter("auto_backup_timezone", DEFAULT_TIMEZONE) or "").strip()
        return cls(
            enabled=_coerce_bool(getter("auto_backup_enabled", False)),
            local_time=raw_time or DEFAULT_LOCAL_TIME,
            timezone=raw_zone or DEFAULT_TIMEZONE,
        )


def validate(settings: BackupSettings) -> BackupSettings:
    """校验时间与时区；非法一律抛 ``BackupScheduleError``。"""
    try:
        ZoneInfo(settings.timezone)
        hour, minute = (int(part) for part in settings.local_time.split(":"))
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise BackupScheduleError(INVALID_TIMEZONE_OR_TIME) from exc
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise BackupScheduleError(INVALID_TIMEZONE_OR_TIME)
    return settings


def validate_local_time(value: Any) -> str:
    """给配置保存用的轻量校验：返回规范化 HH:MM，非法抛错。"""
    text = str(value or "").strip()
    try:
        hour, minute = (int(part) for part in text.split(":"))
    except ValueError as exc:
        raise BackupScheduleError(INVALID_TIMEZONE_OR_TIME) from exc
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise BackupScheduleError(INVALID_TIMEZONE_OR_TIME)
    return f"{hour:02d}:{minute:02d}"


def validate_timezone(value: Any) -> str:
    text = str(value or "").strip() or DEFAULT_TIMEZONE
    try:
        ZoneInfo(text)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise BackupScheduleError(INVALID_TIMEZONE_OR_TIME) from exc
    return text


class BackupScheduleService:
    """把核配置里的备份计划映射成 AstrBot cron 任务。"""

    def __init__(
        self,
        cron_manager: Any,
        settings_loader: Callable[[], BackupSettings],
        handler: Callable[[BackupSettings], Any],
    ) -> None:
        self.cron = cron_manager
        self.load_settings = settings_loader
        self.handler = handler
        self.ready = False
        #: 上次 rebuild 时的校验错误（供 UI / 诊断显示，不影响启动）
        self.last_error = ""

    def current(self) -> BackupSettings:
        return validate(self.load_settings())

    def next_run(self, settings: BackupSettings, now: datetime | None = None) -> datetime | None:
        if not settings.enabled:
            return None
        zone = ZoneInfo(settings.timezone)
        local = (now or utc_now()).astimezone(zone)
        hour, minute = map(int, settings.local_time.split(":"))
        candidate = local.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if candidate <= local:
            candidate += timedelta(days=1)
        return candidate

    async def _runtime_handler(self) -> None:
        """到点时重新读配置：期间被关掉就跳过。"""
        try:
            settings = self.current()
        except BackupScheduleError:
            self.last_error = INVALID_TIMEZONE_OR_TIME
            return
        if not settings.enabled:
            return
        await self.handler(settings)

    async def rebuild(self) -> None:
        """按当前配置注册/移除任务；配置非法时只记录错误，绝不打断插件启动。"""
        await self.remove_job()
        try:
            settings = self.current()
        except BackupScheduleError as exc:
            self.last_error = str(exc)
            self.ready = True
            return
        self.last_error = ""
        if settings.enabled:
            hour, minute = map(int, settings.local_time.split(":"))
            add = getattr(self.cron, "add_basic_job", None)
            if not callable(add):
                self.last_error = CRON_UNAVAILABLE
                self.ready = True
                return
            result = add(
                name=JOB_ID,
                cron_expression=f"{minute} {hour} * * *",
                handler=self._runtime_handler,
                timezone=settings.timezone,
            )
            if hasattr(result, "__await__"):
                await result
        self.ready = True

    async def remove_job(self) -> None:
        await remove_named_cron_jobs(self.cron, JOB_ID)

    async def close(self) -> None:
        await self.remove_job()
