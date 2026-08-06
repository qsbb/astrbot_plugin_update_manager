"""统一驱动手动和定时批次，保证进程内及跨进程串行。"""

from __future__ import annotations

import asyncio
import time
from uuid import uuid4

from .adapters.storage import AtomicJsonStore, FileLeaseLock
from .models import FailurePolicy, TxState, UpdatePlan, utc_now


class UpdateBusyError(RuntimeError):
    pass


class PlanAlreadyExecutedError(RuntimeError):
    pass


class UpdateCoordinator:
    def __init__(
        self, catalog, planner, transaction, store: AtomicJsonStore, diagnostic=None
    ) -> None:
        self.catalog, self.planner, self.transaction, self.store = (
            catalog,
            planner,
            transaction,
            store,
        )
        self._lock = asyncio.Lock()
        self._file_lock = FileLeaseLock(store.root / "locks" / "update.lock")
        self._cancelled = False
        self.diagnostic = diagnostic

    def _emit(
        self,
        code: str,
        summary: str,
        *,
        level: str = "INFO",
        details: dict | None = None,
    ) -> None:
        if not callable(self.diagnostic):
            return
        try:
            self.diagnostic(code, summary, level=level, details=details)
        except Exception:
            pass

    def cancel(self) -> None:
        self._cancelled = True
        self._emit(
            "run.cancel.requested",
            "已请求在下一事务边界停止批次",
            level="WARNING",
            details={
                "component": "coordinator",
                "operation": "cancel",
                "outcome": "requested",
            },
        )

    @property
    def busy(self) -> bool:
        return self._lock.locked()

    async def manual_rollback(self, tx_id: str) -> dict:
        if self._lock.locked():
            self._emit(
                "rollback.manual.rejected",
                "人工回滚被进程锁拒绝",
                level="WARNING",
                details={
                    "component": "coordinator",
                    "operation": "manual_rollback",
                    "outcome": "busy",
                    "reason": "PROCESS_LOCKED",
                },
            )
            raise UpdateBusyError("UPDATE_LOCKED")
        async with self._lock:
            async with self._file_lock.hold() as acquired:
                if not acquired:
                    self._emit(
                        "rollback.manual.rejected",
                        "人工回滚被文件锁拒绝",
                        level="WARNING",
                        details={
                            "component": "coordinator",
                            "operation": "manual_rollback",
                            "outcome": "busy",
                            "reason": "FILE_LOCKED",
                        },
                    )
                    raise UpdateBusyError("UPDATE_LOCKED")
                return await self.transaction.manual_rollback(tx_id)

    async def execute(
        self,
        plan: UpdatePlan,
        *,
        astrbot_version: str,
        rule_revision: int | None,
        on_failure: FailurePolicy = FailurePolicy.CONTINUE,
        trigger: str = "manual",
    ) -> dict:
        started = time.monotonic()
        if self._lock.locked():
            self._emit(
                "run.rejected",
                "更新批次被进程锁拒绝",
                level="WARNING",
                details={
                    "component": "coordinator",
                    "operation": "execute",
                    "outcome": "busy",
                    "reason": "PROCESS_LOCKED",
                },
            )
            raise UpdateBusyError("UPDATE_LOCKED")
        async with self._lock:
            async with self._file_lock.hold() as acquired:
                if not acquired:
                    self._emit(
                        "run.rejected",
                        "更新批次被文件锁拒绝",
                        level="WARNING",
                        details={
                            "component": "coordinator",
                            "operation": "execute",
                            "outcome": "busy",
                            "reason": "FILE_LOCKED",
                        },
                    )
                    raise UpdateBusyError("UPDATE_LOCKED")
                receipts = self.store.read("executed-plans.json", {}) or {}
                if plan.plan_hash in receipts:
                    self._emit(
                        "run.rejected",
                        "更新计划已执行，拒绝重复运行",
                        level="WARNING",
                        details={
                            "component": "coordinator",
                            "operation": "execute",
                            "outcome": "rejected",
                            "reason": "PLAN_ALREADY_EXECUTED",
                        },
                    )
                    raise PlanAlreadyExecutedError("PLAN_ALREADY_EXECUTED")
                current = await self.catalog.scan()
                self.planner.validate(
                    plan,
                    current,
                    astrbot_version=astrbot_version,
                    rule_revision=rule_revision,
                )
                run_id = uuid4().hex
                run = {
                    "run_id": run_id,
                    "plan_hash": plan.plan_hash,
                    "trigger": trigger,
                    "started_at": utc_now().isoformat(),
                    "results": [],
                }
                self.store.write(f"run-{run_id}.json", run)
                self._emit(
                    "run.started",
                    "更新批次开始执行",
                    details={
                        "component": "coordinator",
                        "operation": "execute",
                        "outcome": "started",
                        "run_ref": run_id[:12],
                        "trigger": trigger,
                        "item_count": len(plan.items),
                        "failure_policy": on_failure.value,
                    },
                )
                self._cancelled = False
                for item in plan.items:
                    if self._cancelled:
                        run["cancelled"] = True
                        self._emit(
                            "run.cancelled",
                            "更新批次已在事务边界停止",
                            level="WARNING",
                            details={
                                "component": "coordinator",
                                "operation": "execute",
                                "run_ref": run_id[:12],
                                "outcome": "cancelled",
                            },
                        )
                        break
                    result = await self.transaction.execute(run_id, item)
                    run["results"].append(result)
                    self.store.write(f"run-{run_id}.json", run)
                    self._emit(
                        "run.item.completed",
                        f"{item.plugin_id} 更新项执行完成",
                        level=(
                            "INFO"
                            if result["state"] == TxState.COMMITTED.value
                            else "WARNING"
                        ),
                        details={
                            "component": "coordinator",
                            "operation": "execute_item",
                            "run_ref": run_id[:12],
                            "plugin_id": item.plugin_id,
                            "state": result["state"],
                            "outcome": "completed",
                        },
                    )
                    if result["state"] == TxState.ROLLBACK_FAILED.value or (
                        result["state"] != TxState.COMMITTED.value
                        and on_failure is FailurePolicy.STOP
                    ):
                        break
                run["finished_at"] = utc_now().isoformat()
                receipts[plan.plan_hash] = {
                    "run_id": run_id,
                    "finished_at": run["finished_at"],
                }
                self.store.write("executed-plans.json", receipts)
                self.store.write(f"run-{run_id}.json", run)
                states = [str(item.get("state", "")) for item in run["results"]]
                failed_count = sum(
                    1 for state in states if state != TxState.COMMITTED.value
                )
                cancelled = bool(run.get("cancelled"))
                self._emit(
                    "run.completed",
                    "更新批次执行完成",
                    level="WARNING" if failed_count or cancelled else "INFO",
                    details={
                        "component": "coordinator",
                        "operation": "execute",
                        "outcome": (
                            "cancelled"
                            if cancelled
                            else "partial_failure"
                            if failed_count
                            else "success"
                        ),
                        "run_ref": run_id[:12],
                        "trigger": trigger,
                        "item_count": len(plan.items),
                        "completed_count": len(states),
                        "failed_count": failed_count,
                        "duration_ms": round(
                            (time.monotonic() - started) * 1000,
                            3,
                        ),
                    },
                )
                return run

    def recover_interrupted(self) -> int:
        recovered = 0
        for path in self.store.root.glob("tx-*.json"):
            record = self.store.read(path.name, {})
            if record.get("state") not in {
                "COMMITTED",
                "ROLLED_BACK",
                "ROLLBACK_FAILED",
            }:
                record["state"] = "INTERRUPTED"
                record["recovery_required"] = True
                self.store.write(path.name, record)
                recovered += 1
        self._emit(
            "transaction.recovery.completed",
            "中断事务恢复扫描完成",
            level="WARNING" if recovered else "DEBUG",
            details={
                "component": "coordinator",
                "operation": "recover_interrupted",
                "outcome": "recovered" if recovered else "clean",
                "recovered_count": recovered,
            },
        )
        return recovered
