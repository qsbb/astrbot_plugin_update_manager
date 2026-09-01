"""原子 JSON、审计与跨进程锁持久层。"""

from __future__ import annotations

import json
import os
import re
import tempfile
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator

_TOKEN_RE = re.compile(
    r"(?i)(token|authorization|password|secret)([\s\"':=]+)([^\s,}\"]+)"
)


def redact(value: Any) -> str:
    text = str(value)
    text = _TOKEN_RE.sub(lambda m: f"{m.group(1)}{m.group(2)}***", text)
    text = re.sub(r"(?i)(https?://)[^/@\s]+@", r"\1***@", text)
    return text[:2000]


def contained(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
        return True
    except ValueError:
        return False


class AtomicJsonStore:
    def __init__(self, data_root: Path) -> None:
        self.root = data_root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def path(self, name: str) -> Path:
        if not re.fullmatch(r"[a-zA-Z0-9_.-]+", name):
            raise ValueError("非法存储名称")
        target = self.root / name
        if not contained(target, self.root):
            raise ValueError("存储路径逃逸")
        return target

    def read(self, name: str, default: Any = None) -> Any:
        path = self.path(name)
        if not path.exists():
            return default
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def names(self, prefix: str = "") -> list[str]:
        """列举数据根目录下的存储名（仅本层 .json 文件，不含子目录）。"""
        if not re.fullmatch(r"[a-zA-Z0-9_.-]*", prefix):
            raise ValueError("非法存储前缀")
        try:
            entries = sorted(self.root.iterdir())
        except OSError:
            return []
        return [
            entry.name
            for entry in entries
            if entry.is_file()
            and entry.name.endswith(".json")
            and not entry.name.startswith(".")
            and entry.name.startswith(prefix)
        ]

    def write(self, name: str, value: Any) -> None:
        target = self.path(name)
        fd, temporary = tempfile.mkstemp(prefix=f".{target.name}.", dir=str(self.root))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(value, handle, ensure_ascii=False, sort_keys=True, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, target)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def append_audit(self, record: dict[str, Any]) -> None:
        audit = self.root / "audit"
        audit.mkdir(exist_ok=True)
        date = time.strftime("%Y-%m-%d", time.gmtime())
        path = audit / f"{date}.jsonl"
        sanitized = {
            key: redact(val) if key in {"error", "detail", "source_url"} else val
            for key, val in record.items()
        }
        with path.open("a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(sanitized, ensure_ascii=False, sort_keys=True) + "\n"
            )
            handle.flush()


class FileLeaseLock:
    def __init__(self, path: Path, *, lease_seconds: int = 3600) -> None:
        self.path = path
        self.lease_seconds = lease_seconds
        self._owned = False

    def acquire(self) -> bool:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps({"pid": os.getpid(), "started_at": time.time()})
        for _ in range(2):
            try:
                fd = os.open(str(self.path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    handle.write(payload)
                self._owned = True
                return True
            except FileExistsError:
                try:
                    age = time.time() - self.path.stat().st_mtime
                    if age <= self.lease_seconds:
                        return False
                    self.path.unlink()
                except FileNotFoundError:
                    continue
        return False

    def release(self) -> None:
        if self._owned:
            try:
                self.path.unlink()
            except FileNotFoundError:
                pass
            self._owned = False

    @asynccontextmanager
    async def hold(self) -> AsyncIterator[bool]:
        acquired = self.acquire()
        try:
            yield acquired
        finally:
            if acquired:
                self.release()
