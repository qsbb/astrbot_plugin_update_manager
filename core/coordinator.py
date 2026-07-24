"""统一驱动手动和定时批次，保证进程内及跨进程串行。"""

from __future__ import annotations

import asyncio
from uuid import uuid4

from .adapters.storage import AtomicJsonStore, FileLeaseLock
from .models import FailurePolicy, TxState, UpdatePlan, utc_now


class UpdateBusyError(RuntimeError):
    pass


class PlanAlreadyExecutedError(RuntimeError):
    pass


class UpdateCoordinator:
    def __init__(self, catalog, planner, transaction, store: AtomicJsonStore) -> None:
        self.catalog, self.planner, self.transaction, self.store = (
            catalog,
            planner,
            transaction,
            store,
        )
        self._lock = asyncio.Lock()
        self._file_lock = FileLeaseLock(store.root / "locks" / "update.lock")
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    @property
    def busy(self) -> bool:
        return self._lock.locked()

    async def manual_rollback(self, tx_id: str) -> dict:
        if self._lock.locked():
            raise UpdateBusyError("UPDATE_LOCKED")
        async with self._lock:
            async with self._file_lock.hold() as acquired:
                if not acquired:
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
        if self._lock.locked():
            raise UpdateBusyError("UPDATE_LOCKED")
        async with self._lock:
            async with self._file_lock.hold() as acquired:
                if not acquired:
                    raise UpdateBusyError("UPDATE_LOCKED")
                receipts = self.store.read("executed-plans.json", {}) or {}
                if plan.plan_hash in receipts:
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
                self._cancelled = False
                for item in plan.items:
                    if self._cancelled:
                        run["cancelled"] = True
                        break
                    result = await self.transaction.execute(run_id, item)
                    run["results"].append(result)
                    self.store.write(f"run-{run_id}.json", run)
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
        return recovered
