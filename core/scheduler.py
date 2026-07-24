"""每日规则持久化、CAS revision、时区、jitter 与 runtime job 恢复。"""

from __future__ import annotations

import asyncio
import random
from dataclasses import replace
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .models import UpdateRule, utc_now


class RuleConflictError(RuntimeError):
    pass


class RuleValidationError(ValueError):
    pass


class ScheduleService:
    JOB_ID = "astrbot_plugin_update_manager_daily"

    def __init__(self, cron_manager, store, handler) -> None:
        self.cron = cron_manager
        self.store = store
        self.handler = handler
        self._tasks: set[asyncio.Task] = set()
        self.ready = False

    def load(self) -> UpdateRule:
        raw = self.store.read("rule.json", None)
        return UpdateRule() if raw is None else self.validate(UpdateRule.from_dict(raw))

    def validate(self, rule: UpdateRule) -> UpdateRule:
        try:
            ZoneInfo(rule.timezone)
            hour, minute = (int(value) for value in rule.local_time.split(":"))
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise RuleValidationError("INVALID_TIMEZONE_OR_TIME") from exc
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise RuleValidationError("INVALID_LOCAL_TIME")
        if not (
            0 <= rule.jitter_minutes <= 120
            and 0 <= rule.misfire_grace_minutes <= 1440
            and 0 <= rule.minimum_release_age_hours <= 24 * 365
        ):
            raise RuleValidationError("INVALID_SCHEDULE_RANGE")
        if rule.policy not in {"check_only", "patch", "minor", "stable"}:
            raise RuleValidationError("INVALID_POLICY")
        if rule.on_failure not in {"rollback_continue", "rollback_stop"}:
            raise RuleValidationError("INVALID_FAILURE_POLICY")
        if any(not plugin_id or len(plugin_id) > 128 for plugin_id in rule.plugin_ids):
            raise RuleValidationError("INVALID_PLUGIN_ID")
        if rule.enabled and not rule.plugin_ids:
            raise RuleValidationError("EMPTY_ENABLED_RULE")
        return rule

    def save(self, rule: UpdateRule, *, expected_revision: int) -> UpdateRule:
        current = self.load()
        if current.revision != expected_revision:
            raise RuleConflictError("RULE_REVISION_CONFLICT")
        updated = self.validate(
            replace(
                rule, revision=current.revision + 1, updated_at=utc_now().isoformat()
            )
        )
        self.store.write("rule.json", updated.to_dict())
        return updated

    def next_run(
        self, rule: UpdateRule, now: datetime | None = None
    ) -> datetime | None:
        if not rule.enabled:
            return None
        zone = ZoneInfo(rule.timezone)
        local = (now or utc_now()).astimezone(zone)
        hour, minute = map(int, rule.local_time.split(":"))
        candidate = local.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if candidate <= local:
            candidate += timedelta(days=1)
        return candidate

    async def _runtime_handler(self, expected_revision: int) -> None:
        rule = self.load()
        if not rule.enabled or rule.revision != expected_revision:
            return
        if rule.jitter_minutes:
            await asyncio.sleep(random.randint(0, rule.jitter_minutes * 60))
        latest = self.load()
        if latest.enabled and latest.revision == expected_revision:
            await self.handler(latest)

    async def rebuild(self) -> None:
        await self.remove_job()
        rule = self.load()
        if rule.enabled:
            hour, minute = map(int, rule.local_time.split(":"))
            cron = f"{minute} {hour} * * *"
            add = getattr(self.cron, "add_basic_job", None)
            if not callable(add):
                raise RuleValidationError("CRON_UNAVAILABLE")
            result = add(
                name=self.JOB_ID,
                cron_expression=cron,
                handler=lambda: self._runtime_handler(rule.revision),
                timezone=rule.timezone,
            )
            if hasattr(result, "__await__"):
                await result
        self.ready = True

    async def remove_job(self) -> None:
        if self.cron is None:
            return
        for method_name in ("delete_job", "remove_job"):
            method = getattr(self.cron, method_name, None)
            if callable(method):
                try:
                    result = method(self.JOB_ID)
                    if hasattr(result, "__await__"):
                        await result
                except (KeyError, ValueError):
                    pass
                break

    async def close(self) -> None:
        await self.remove_job()
        for task in tuple(self._tasks):
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        self.ready = False
