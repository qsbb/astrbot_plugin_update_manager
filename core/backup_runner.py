"""核的「自动备份」执行器：走 AstrBot 官方导出器，可指定保存目录。

边界与约定：
- 只调用 AstrBot 官方 ``astrbot.core.backup.exporter.AstrBotExporter``，不自己实现打包；
- 官方链路不可用（老版本 / 导入失败）一律 fail-closed，返回明确错误码；
- 全程只读插件侧状态，不改 AstrBot 代码；备份结果只写调用方给的目录。
"""

from __future__ import annotations

import asyncio
import os
import time
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..series_diagnostics import _safe_text, diagnostic_event, diagnostic_operation

#: 官方导出器的文件命名：astrbot_backup_<YYYYmmdd_HHMMSS>.zip
BACKUP_FILE_PREFIX = "astrbot_backup_"
BACKUP_FILE_SUFFIX = ".zip"
WRITE_PROBE_NAME = ".update-manager-backup-probe"

ERROR_EXPORTER_UNAVAILABLE = "OFFICIAL_BACKUP_UNAVAILABLE"
ERROR_DIR_NOT_ABSOLUTE = "BACKUP_DIR_NOT_ABSOLUTE"
ERROR_DIR_NOT_WRITABLE = "BACKUP_DIR_NOT_WRITABLE"
ERROR_DIR_INSIDE_SOURCE = "BACKUP_DIR_INSIDE_SOURCE"
ERROR_DIR_INVALID = "BACKUP_DIR_INVALID"
ERROR_ALREADY_RUNNING = "BACKUP_ALREADY_RUNNING"
ERROR_RUN_FAILED = "BACKUP_FAILED"
ERROR_DELETE_INVALID_NAME = "BACKUP_DELETE_INVALID_NAME"
ERROR_DELETE_NOT_FOUND = "BACKUP_DELETE_NOT_FOUND"
ERROR_DELETE_FAILED = "BACKUP_DELETE_FAILED"


class OfficialBackupUnavailable(RuntimeError):
    """AstrBot 没有可用的官方备份链路（版本过旧或导入失败）。"""


@dataclass(frozen=True, slots=True)
class BackupPaths:
    """AstrBot 官方路径：数据目录、默认备份目录、备份源目录（禁止把备份存进去）。"""

    data_dir: str
    default_dir: str
    source_dirs: tuple[str, ...]


def _now() -> str:
    return datetime.now(UTC).astimezone().isoformat(timespec="seconds")


def official_paths() -> BackupPaths:
    """读取 AstrBot 官方路径定义；不可用则抛 ``OfficialBackupUnavailable``。"""
    try:
        from astrbot.core.backup import constants as backup_constants
        from astrbot.core.utils.astrbot_path import (
            get_astrbot_backups_path,
            get_astrbot_data_path,
        )
    except Exception as exc:  # noqa: BLE001 - 版本差异也要 fail-closed
        raise OfficialBackupUnavailable(str(exc) or "official backup module missing") from exc
    try:
        directories = backup_constants.get_backup_directories()
    except Exception as exc:  # noqa: BLE001
        raise OfficialBackupUnavailable(str(exc) or "backup directories unavailable") from exc
    return BackupPaths(
        data_dir=str(Path(get_astrbot_data_path()).resolve()),
        default_dir=str(Path(get_astrbot_backups_path()).resolve()),
        source_dirs=tuple(
            str(Path(str(value)).resolve()) for value in directories.values() if value
        ),
    )


def load_exporter() -> Any:
    """懒加载官方导出器；不可用则抛 ``OfficialBackupUnavailable``。"""
    try:
        from astrbot.core.backup.exporter import AstrBotExporter
    except Exception as exc:  # noqa: BLE001
        raise OfficialBackupUnavailable(str(exc) or "official exporter missing") from exc
    return AstrBotExporter


def _inside(child: Path, parent: Path) -> bool:
    return child == parent or parent in child.parents


def volume_root(path: Path, *, ismount: Any = os.path.ismount) -> Path:
    """向上找到 path 所在的"最外层挂载卷"；返回 "/" 表示落在容器文件系统里。

    Container 里只有 bind mount 出来的目录是持久卷（例如 AstrBot 的 data 目录）；
    其它路径虽然看着像宿主目录，其实写在容器可写层，容器重建/升级就没了。
    """
    current = path if path.is_dir() else path.parent
    while current != current.parent:
        try:
            if ismount(str(current)):
                return current
        except OSError:
            break
        current = current.parent
    return current




def resolve_target_dir(raw: str, paths: BackupPaths) -> tuple[str, str]:
    """留空 → 官方默认目录；非空必须是绝对路径。返回 (绝对目录, 错误码)。"""
    text = str(raw or "").strip()
    if not text:
        return paths.default_dir, ""
    try:
        candidate = Path(text).expanduser()
    except (OSError, ValueError):
        # 路径本身非法（例如含空字节）
        return "", ERROR_DIR_INVALID
    if not candidate.is_absolute():
        return "", ERROR_DIR_NOT_ABSOLUTE
    try:
        return str(candidate.resolve()), ""
    except (OSError, ValueError):
        return "", ERROR_DIR_INVALID


def validate_dir(raw: str, *, paths: BackupPaths | None = None) -> dict[str, Any]:
    """校验备份目录：绝对路径、可创建可写、且不在官方备份源目录内部。"""
    try:
        resolved_paths = paths or official_paths()
    except OfficialBackupUnavailable:
        return {"ok": False, "path": "", "error": ERROR_EXPORTER_UNAVAILABLE, "ephemeral": False, "volume": ""}
    target, error = resolve_target_dir(raw, resolved_paths)
    if error:
        return {"ok": False, "path": "", "error": error, "ephemeral": False, "volume": ""}
    resolved = Path(target)
    for source in resolved_paths.source_dirs:
        if _inside(resolved, Path(source)):
            return {"ok": False, "path": target, "error": ERROR_DIR_INSIDE_SOURCE, "ephemeral": False, "volume": ""}
    try:
        resolved.mkdir(parents=True, exist_ok=True)
        probe = resolved / WRITE_PROBE_NAME
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except (OSError, ValueError):
        # ValueError：路径里含空字节等非法字符（Path.mkdir 不抛 OSError）
        return {"ok": False, "path": target, "error": ERROR_DIR_NOT_WRITABLE, "ephemeral": False, "volume": ""}
    volume = volume_root(resolved)
    return {
        "ok": True,
        "path": str(resolved),
        "error": "",
        #: 落在容器文件系统里（非挂载卷）：容器重建/升级后备份会丢，UI 要告警
        "ephemeral": str(volume) == os.sep,
        "volume": str(volume),
    }


def _is_complete_zip(target: Path) -> bool:
    """官方导出器直接写最终文件名：中途被打断会留下截断文件，必须标出来。

    ``zipfile.is_zipfile`` 只读中央目录，对大文件也是常数级开销。
    """
    try:
        return zipfile.is_zipfile(target)
    except OSError:
        return False


def _backup_files(target: Path) -> list[dict[str, Any]]:
    files: list[dict[str, Any]] = []
    for item in target.iterdir():
        if not item.is_file():
            continue
        if not item.name.startswith(BACKUP_FILE_PREFIX) or not item.name.endswith(BACKUP_FILE_SUFFIX):
            continue
        stat = item.stat()
        files.append(
            {
                "name": item.name,
                "size": stat.st_size,
                "modified_at": datetime.fromtimestamp(stat.st_mtime)
                .astimezone()
                .isoformat(timespec="seconds"),
                #: False = 可能是中断留下的截断/损坏文件，别当恢复点用
                "valid": _is_complete_zip(item),
            }
        )
    files.sort(key=lambda item: item["modified_at"], reverse=True)
    return files


def list_backups(raw_dir: str, *, paths: BackupPaths | None = None) -> dict[str, Any]:
    """列出目标目录里的官方备份文件与占用（只认 astrbot_backup_*.zip）。"""
    check = validate_dir(raw_dir, paths=paths)
    if not check["ok"]:
        return {
            "success": False,
            "error": check["error"],
            "dir": check["path"],
            "files": [],
            "total_bytes": 0,
        }
    target = Path(check["path"])
    try:
        files = _backup_files(target)
    except OSError as exc:
        return {
            "success": False,
            "error": ERROR_DIR_NOT_WRITABLE,
            "detail": _safe_text(exc, limit=200),
            "dir": str(target),
            "files": [],
            "total_bytes": 0,
        }
    return {
        "success": True,
        "dir": str(target),
        "files": files,
        "total_bytes": sum(int(item["size"]) for item in files),
    }


def delete_backup(
    raw_dir: str, filename: str, *, paths: BackupPaths | None = None
) -> dict[str, Any]:
    """删除目标目录下的某个官方备份（严格校验文件名，防路径穿越）。"""
    check = validate_dir(raw_dir, paths=paths)
    if not check["ok"]:
        return {"success": False, "error": check["error"]}
    name = str(filename or "").strip()
    if (
        not name
        or Path(name).name != name
        or not name.startswith(BACKUP_FILE_PREFIX)
        or not name.endswith(BACKUP_FILE_SUFFIX)
    ):
        return {"success": False, "error": ERROR_DELETE_INVALID_NAME}
    target = Path(check["path"]) / name
    if not target.is_file():
        return {"success": False, "error": ERROR_DELETE_NOT_FOUND}
    try:
        target.unlink()
    except OSError as exc:
        return {
            "success": False,
            "error": ERROR_DELETE_FAILED,
            "detail": _safe_text(exc, limit=200),
        }
    return {"success": True, "name": name, "dir": check["path"]}


class BackupRunner:
    """执行官方备份；同一时刻只允许一个备份在跑，结果只保留在内存 + 核的 store。"""

    STATE_FILE = "backup-state.json"

    def __init__(self, context: Any, *, store: Any = None) -> None:
        self.context = context
        self.store = store
        self._lock = asyncio.Lock()
        self._state: dict[str, Any] = {
            "running": False,
            "stage": "",
            "current": 0,
            "total": 0,
            "message": "",
            "started_at": "",
            "last_result": None,
        }
        if store is not None:
            # 状态文件损坏（截断/手改）不能影响插件启动：读失败就当没有历史结果。
            try:
                saved = store.read(self.STATE_FILE, None)
            except Exception:  # noqa: BLE001
                saved = None
            if isinstance(saved, dict) and isinstance(saved.get("last_result"), dict):
                self._state["last_result"] = saved["last_result"]

    @property
    def running(self) -> bool:
        return self._lock.locked()

    def status(self) -> dict[str, Any]:
        state = dict(self._state)
        state["running"] = self.running
        progress = 0
        total = int(state.get("total") or 0)
        current = int(state.get("current") or 0)
        if total > 0:
            progress = max(0, min(100, round(current / total * 100)))
        state["progress"] = progress
        return {"success": True, **state}

    @staticmethod
    def _align_ownership(artifact: Path, target_dir: Path) -> bool:
        """把备份文件属主对齐到目标目录（best-effort）。

        容器以 root 写宿主/NAS 目录时，文件默认是 root:root 0700 —— 目录属主
        在文件管理器里能看能删却下载不了。目标目录属于真实用户时，把文件改成
        该用户所有并保持 0600（备份含配置与密钥，不做全局可读）。
        """
        try:
            info = target_dir.stat()
        except OSError:
            return False
        if info.st_uid == 0:
            return False  # 目录本身是 root 的（如官方默认目录），保持原样
        try:
            os.chown(artifact, info.st_uid, info.st_gid)
            os.chmod(artifact, 0o600)
        except (OSError, AttributeError):
            return False
        return True

    def _persist(self, result: dict[str, Any]) -> None:
        self._state["last_result"] = result
        if self.store is None:
            return
        try:
            self.store.write(self.STATE_FILE, {"last_result": result})
        except Exception:  # noqa: BLE001 - 持久化失败不影响备份本身
            pass

    def _main_db(self) -> Any:
        getter = getattr(self.context, "get_db", None)
        if not callable(getter):
            return None
        try:
            return getter()
        except Exception:  # noqa: BLE001
            return None

    async def run(self, *, target_dir: str = "", trigger: str = "manual") -> dict[str, Any]:
        """执行一次官方备份。返回结构化结果，绝不抛异常给调用方。"""
        if self._lock.locked():
            diagnostic_operation(
                "backup",
                "run",
                "自动备份已在运行，本次跳过",
                level="WARNING",
                emit_start=False,
            ).event(
                "skipped",
                "已有备份在运行，跳过触发",
                level="WARNING",
                details={"trigger": _safe_text(trigger, limit=32)},
            )
            return {
                "success": False,
                "error": ERROR_ALREADY_RUNNING,
                "skipped": True,
                "trigger": trigger,
            }

        try:
            paths = official_paths()
            exporter_cls = load_exporter()
        except OfficialBackupUnavailable as exc:
            return {
                "success": False,
                "error": ERROR_EXPORTER_UNAVAILABLE,
                "detail": _safe_text(exc, limit=200),
            }

        check = validate_dir(target_dir, paths=paths)
        if not check["ok"]:
            return {
                "success": False,
                "error": check["error"],
                "dir": check["path"],
            }

        if check.get("ephemeral"):
            # 看着像宿主目录、其实是容器可写层：容器重建/升级就丢，必须留痕
            diagnostic_event(
                "backup.run.warning",
                f"备份目录不在挂载卷上（容器文件系统内），容器重建后备份会丢失：{check['path']}",
                level="WARNING",
                details={"dir": check["path"], "volume": str(check.get("volume") or os.sep)},
            )

        main_db = self._main_db()
        if main_db is None:
            return {
                "success": False,
                "error": ERROR_EXPORTER_UNAVAILABLE,
                "detail": "无法从 AstrBot Context 获取主数据库",
            }
        kb_manager = getattr(self.context, "kb_manager", None)
        config_path = os.path.join(paths.data_dir, "cmd_config.json")

        async with self._lock:
            operation = diagnostic_operation(
                "backup",
                "run",
                "AstrBot 官方备份",
                details={
                    "trigger": _safe_text(trigger, limit=32),
                    "dir": check["path"],
                    "kb_included": kb_manager is not None,
                },
            )
            started = time.perf_counter()
            self._state.update(
                {
                    "running": True,
                    "stage": "starting",
                    "current": 0,
                    "total": 0,
                    "message": "正在初始化官方导出器…",
                    "started_at": _now(),
                }
            )

            async def progress(
                stage: Any, current: Any, total: Any, message: Any = ""
            ) -> None:
                self._state.update(
                    {
                        "stage": _safe_text(stage, limit=40),
                        "current": int(current or 0),
                        "total": int(total or 0),
                        "message": _safe_text(message, limit=160),
                    }
                )

            try:
                exporter = exporter_cls(
                    main_db=main_db,
                    kb_manager=kb_manager,
                    config_path=config_path,
                )
                zip_path = await exporter.export_all(
                    output_dir=check["path"], progress_callback=progress
                )
            except Exception as exc:  # noqa: BLE001 - 备份失败不能外抛
                operation.fail(exc, summary="AstrBot 官方备份失败")
                result = {
                    "success": False,
                    "error": ERROR_RUN_FAILED,
                    "detail": _safe_text(exc, limit=200),
                    "trigger": trigger,
                    "dir": check["path"],
                    "finished_at": _now(),
                }
            else:
                path = Path(str(zip_path))
                try:
                    size = path.stat().st_size
                except OSError:
                    size = 0
                aligned = self._align_ownership(path, Path(check["path"]))
                result = {
                    "success": True,
                    "trigger": trigger,
                    "dir": check["path"],
                    "zip_path": str(path),
                    "filename": path.name,
                    "size_bytes": size,
                    "duration_ms": round((time.perf_counter() - started) * 1000),
                    "kb_included": kb_manager is not None,
                    #: 目标目录属于某个真实用户时会顺带对齐属主/权限（便于在 NAS 上直接下载）
                    "ownership_aligned": aligned,
                    "finished_at": _now(),
                }
                operation.finish(
                    summary="AstrBot 官方备份完成",
                    details={"filename": path.name, "size_bytes": size},
                )
            finally:
                self._state.update(
                    {
                        "running": False,
                        "stage": "",
                        "current": 0,
                        "total": 0,
                        "message": "",
                    }
                )
            self._persist(result)
            return result
