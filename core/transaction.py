"""备份、官方核心更新、健康检查与自动回滚事务。"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
from dataclasses import asdict
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

from .adapters.storage import AtomicJsonStore, contained, redact
from .models import PlanItem, TxState, utc_now


class TransactionError(RuntimeError):
    pass


def tree_manifest(root: Path) -> tuple[list[dict[str, object]], str]:
    files: list[dict[str, object]] = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise TransactionError("SYMLINK_BACKUP_BLOCKED")
        if path.is_file():
            rel = path.relative_to(root).as_posix()
            if "__pycache__" in path.parts or rel.endswith((".pyc", ".pyo")):
                continue
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            files.append({"path": rel, "size": path.stat().st_size, "sha256": digest})
    return files, hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()


class PluginTransaction:
    def __init__(
        self,
        adapter,
        health,
        store: AtomicJsonStore,
        *,
        plugin_root: Path,
        backup_root: Path,
        diagnostic=None,
    ) -> None:
        self.adapter, self.health, self.store = adapter, health, store
        self.diagnostic = diagnostic
        self.plugin_root = plugin_root.resolve()
        self.backup_root = backup_root.resolve()
        if not contained(self.backup_root, store.root):
            raise ValueError("备份根目录必须位于插件 data 范围")

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

    @staticmethod
    def _state_level(state: TxState) -> str:
        if state is TxState.ROLLBACK_FAILED:
            return "ERROR"
        if state in {
            TxState.FAILED,
            TxState.ROLLING_BACK,
            TxState.ROLLED_BACK,
            TxState.INTERRUPTED,
        }:
            return "WARNING"
        return "INFO"

    def _record(self, record: dict, state: TxState, **extra) -> None:
        record.update(state=state.value, updated_at=utc_now().isoformat(), **extra)
        self.store.write(f"tx-{record['tx_id']}.json", record)
        self.store.append_audit(
            {
                "event": "transaction",
                "tx_id": record["tx_id"],
                "plugin_id": record["plugin_id"],
                "state": state.value,
                **extra,
            }
        )
        health_result = extra.get("health_result")
        reason = extra.get("error") or extra.get("warning")
        if isinstance(health_result, dict):
            reason = health_result.get("reason") or reason
        self._emit(
            "transaction.state",
            f"{record['plugin_id']} 更新事务进入 {state.value}",
            level=self._state_level(state),
            details={
                "component": "transaction",
                "operation": "plugin_update",
                "plugin_id": record["plugin_id"],
                "from_version": record.get("from_version", ""),
                "to_version": record.get("to_version", ""),
                "state": state.value,
                "tx_ref": str(record["tx_id"])[:12],
                "run_ref": str(record.get("run_id", ""))[:12],
                "reason": reason or state.value,
            },
        )

    def _source(self, item: PlanItem) -> Path:
        if (
            not item.root_dir_name
            or Path(item.root_dir_name).name != item.root_dir_name
        ):
            raise TransactionError("INVALID_PLUGIN_ROOT")
        source = self.plugin_root / item.root_dir_name
        if (
            not contained(source, self.plugin_root)
            or source.is_symlink()
            or not source.is_dir()
        ):
            raise TransactionError("PLUGIN_PATH_ESCAPE")
        return source

    def backup(self, item: PlanItem, tx_id: str) -> tuple[Path, str]:
        source = self._source(item)
        target_parent = self.backup_root / item.plugin_id
        target_parent.mkdir(parents=True, exist_ok=True)
        temporary, ready = target_parent / f".{tx_id}.tmp", target_parent / tx_id
        if temporary.exists():
            shutil.rmtree(temporary)
        shutil.copytree(
            source,
            temporary,
            symlinks=False,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache"),
        )
        manifest, digest = tree_manifest(temporary)
        (temporary / ".update-manager-manifest.json").write_text(
            json.dumps(
                {
                    "plugin_id": item.plugin_id,
                    "root_dir_name": item.root_dir_name,
                    "digest": digest,
                    "files": manifest,
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        os.replace(temporary, ready)
        return ready, digest

    async def rollback(self, item: PlanItem, backup: Path, digest: str) -> None:
        if not contained(backup, self.backup_root) or backup.is_symlink():
            raise TransactionError("BACKUP_PATH_ESCAPE")
        manifest_path = backup / ".update-manager-manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        _files, actual = tree_manifest_without_metadata(backup)
        if (
            manifest.get("plugin_id") != item.plugin_id
            or manifest.get("digest") != digest
            or actual != digest
        ):
            raise TransactionError("BACKUP_DIGEST_MISMATCH")
        destination = self._source_path(item)
        failed = self.store.root / "failed" / f"{item.root_dir_name}-{uuid4().hex}"
        failed.parent.mkdir(exist_ok=True)
        await self.adapter.terminate_plugin(item.plugin_id)
        if destination.exists():
            os.replace(destination, failed)
        shutil.copytree(
            backup,
            destination,
            ignore=shutil.ignore_patterns(".update-manager-manifest.json"),
        )
        await self.adapter.reload_plugin(item.plugin_id)
        result = await self.health.check(
            item.plugin_id, item.from_version, expected_activated=item.activated
        )
        if not result.healthy:
            raise TransactionError(f"ROLLBACK_HEALTH_FAILED:{result.reason}")

    def _source_path(self, item: PlanItem) -> Path:
        path = self.plugin_root / item.root_dir_name
        if not contained(path, self.plugin_root):
            raise TransactionError("PLUGIN_PATH_ESCAPE")
        return path

    async def execute(self, run_id: str, item: PlanItem) -> dict:
        started = time.monotonic()
        tx_id = uuid4().hex
        record = {
            "tx_id": tx_id,
            "run_id": run_id,
            "plugin_id": item.plugin_id,
            "from_version": item.from_version,
            "to_version": item.to_version,
            "root_dir_name": item.root_dir_name,
            "source_kind": item.source_kind,
            "source_url": item.source_url,
            "activated": item.activated,
            "target_digest": item.digest,
            "tag": item.tag,
            "commit": item.commit,
            "published_at": item.published_at,
            "archive_url": item.archive_url,
            "started_at": utc_now().isoformat(),
            "environment_rollback_complete": False,
        }
        self._record(record, TxState.LOCKED)
        backup = None
        digest = None
        try:
            backup, digest = self.backup(item, tx_id)
            self._record(
                record,
                TxState.BACKED_UP,
                backup_path=str(backup.relative_to(self.store.root)),
                backup_digest=digest,
            )
            self._record(record, TxState.CORE_UPDATE_RUNNING)
            await self.adapter.update_plugin(
                item.plugin_id,
                source_kind=item.source_kind,
                source_url=item.source_url,
                archive_url=item.archive_url,
            )
            result = await self.health.check(
                item.plugin_id, item.to_version, expected_activated=item.activated
            )
            if not result.healthy:
                raise TransactionError(f"HEALTH_CHECK_FAILED:{result.reason}")
            self._record(record, TxState.HEALTHY, health_result=asdict(result))
            self._record(record, TxState.COMMITTED, finished_at=utc_now().isoformat())
        except Exception as exc:
            self._record(record, TxState.FAILED, error=redact(exc))
            if backup is None or digest is None:
                record["finished_at"] = utc_now().isoformat()
                self.store.write(f"tx-{record['tx_id']}.json", record)
                self._emit_transaction_completed(record, started)
                return record
            self._record(record, TxState.ROLLING_BACK)
            try:
                await self.rollback(item, backup, digest)
                self._record(
                    record,
                    TxState.ROLLED_BACK,
                    finished_at=utc_now().isoformat(),
                    warning="代码已回滚；共享 Python 依赖可能已变化",
                )
            except Exception as rollback_exc:
                self._record(
                    record,
                    TxState.ROLLBACK_FAILED,
                    finished_at=utc_now().isoformat(),
                    error=redact(rollback_exc),
                )
        self._emit_transaction_completed(record, started)
        return record

    def _emit_transaction_completed(self, record: dict, started: float) -> None:
        state = TxState(record["state"])
        self._emit(
            "transaction.completed",
            f"{record['plugin_id']} 更新事务结束：{state.value}",
            level=self._state_level(state),
            details={
                "component": "transaction",
                "operation": "plugin_update",
                "outcome": "success" if state is TxState.COMMITTED else "failed",
                "plugin_id": record["plugin_id"],
                "state": state.value,
                "tx_ref": str(record["tx_id"])[:12],
                "run_ref": str(record.get("run_id", ""))[:12],
                "duration_ms": round(
                    (time.monotonic() - started) * 1000,
                    3,
                ),
            },
        )

    async def manual_rollback(self, tx_id: str) -> dict:
        """按已提交事务记录恢复其更新前版本，且只接受本插件生成的备份。"""
        started = time.monotonic()
        if not tx_id or len(tx_id) > 64 or not tx_id.isalnum():
            raise TransactionError("INVALID_TRANSACTION_ID")
        original = self.store.read(f"tx-{tx_id}.json", None)
        if (
            not isinstance(original, dict)
            or original.get("state") != TxState.COMMITTED.value
        ):
            raise TransactionError("TRANSACTION_NOT_ROLLBACKABLE")
        required = {
            "plugin_id",
            "root_dir_name",
            "from_version",
            "to_version",
            "source_kind",
            "source_url",
            "activated",
            "backup_path",
            "backup_digest",
        }
        if not required.issubset(original):
            raise TransactionError("TRANSACTION_RECORD_INCOMPLETE")
        item = PlanItem(
            plugin_id=str(original["plugin_id"]),
            root_dir_name=str(original["root_dir_name"]),
            from_version=str(original["from_version"]),
            to_version=str(original["to_version"]),
            source_kind=str(original["source_kind"]),
            source_url=str(original["source_url"]),
            activated=bool(original["activated"]),
            fingerprint="manual-rollback",
        )
        current = await self.adapter.get_plugin(item.plugin_id)
        if current is None or current.version != item.to_version:
            raise TransactionError("ROLLBACK_VERSION_PRECONDITION_FAILED")
        backup = self.store.root / str(original["backup_path"])
        rollback_id = uuid4().hex
        record = {
            "tx_id": rollback_id,
            "run_id": f"manual-rollback-{tx_id}",
            "plugin_id": item.plugin_id,
            "from_version": item.to_version,
            "to_version": item.from_version,
            "original_tx_id": tx_id,
            "started_at": utc_now().isoformat(),
            "environment_rollback_complete": False,
        }
        self._record(record, TxState.ROLLING_BACK)
        try:
            await self.rollback(item, backup, str(original["backup_digest"]))
            self._record(
                record,
                TxState.ROLLED_BACK,
                finished_at=utc_now().isoformat(),
                warning="代码已回滚；共享 Python 依赖可能已变化",
            )
        except Exception as exc:
            self._record(
                record,
                TxState.ROLLBACK_FAILED,
                finished_at=utc_now().isoformat(),
                error=redact(exc),
            )
        state = TxState(record["state"])
        self._emit(
            "rollback.manual.completed",
            f"{record['plugin_id']} 人工回滚结束：{state.value}",
            level=self._state_level(state),
            details={
                "component": "transaction",
                "operation": "manual_rollback",
                "outcome": ("success" if state is TxState.ROLLED_BACK else "failed"),
                "plugin_id": record["plugin_id"],
                "state": state.value,
                "tx_ref": rollback_id[:12],
                "duration_ms": round(
                    (time.monotonic() - started) * 1000,
                    3,
                ),
            },
        )
        return record

    def cleanup(
        self,
        *,
        keep_success: int = 3,
        failed_days: int = 7,
        capacity_bytes: int = 2 * 1024**3,
    ) -> None:
        entries = [
            p
            for p in self.backup_root.glob("*/*")
            if p.is_dir() and not p.name.startswith(".")
        ]
        entries.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        protected: set[Path] = set()
        by_plugin: dict[Path, list[Path]] = {}
        for entry in entries:
            by_plugin.setdefault(entry.parent, []).append(entry)
        for plugin_entries in by_plugin.values():
            protected.update(plugin_entries[: max(1, keep_success)])
        cutoff = utc_now() - timedelta(days=failed_days)
        total = sum(
            sum(f.stat().st_size for f in p.rglob("*") if f.is_file()) for p in entries
        )
        removed_count = 0
        removed_bytes = 0
        for path in reversed(entries):
            if path in protected:
                continue
            old = path.stat().st_mtime < cutoff.timestamp()
            size = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
            if old or total > capacity_bytes:
                shutil.rmtree(path)
                total -= size
                removed_count += 1
                removed_bytes += size
        self._emit(
            "backup.cleanup.completed",
            "备份清理完成",
            level="DEBUG",
            details={
                "component": "backup",
                "operation": "cleanup",
                "outcome": "success",
                "backup_count": len(entries),
                "protected_count": len(protected),
                "removed_count": removed_count,
                "removed_bytes": removed_bytes,
                "remaining_bytes": total,
            },
        )


def tree_manifest_without_metadata(root: Path):
    files = []
    for path in sorted(root.rglob("*")):
        if path.name == ".update-manager-manifest.json":
            continue
        if path.is_symlink():
            raise TransactionError("SYMLINK_BACKUP_BLOCKED")
        if path.is_file():
            rel = path.relative_to(root).as_posix()
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            files.append({"path": rel, "size": path.stat().st_size, "sha256": digest})
    return files, hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()
