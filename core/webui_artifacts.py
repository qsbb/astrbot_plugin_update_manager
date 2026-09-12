"""series.webui@2.0 通用制品存储：文件上传/下载与音频试听的内存载体。

制品是短期数据，不进入插件状态；默认 30 分钟 TTL、单文件 10MB、总量 50MB。
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

MAX_ARTIFACT_BYTES = 10 * 1024 * 1024
MAX_TOTAL_BYTES = 50 * 1024 * 1024
ARTIFACT_TTL_SECONDS = 30 * 60


@dataclass
class ArtifactRecord:
    artifact_id: str
    plugin_id: str
    panel: str
    filename: str
    mime: str
    data: bytes
    created_at: float = field(default_factory=time.time)


class ArtifactStore:
    def __init__(self) -> None:
        self._items: dict[str, ArtifactRecord] = {}

    def _cleanup(self) -> None:
        now = time.time()
        stale = [
            artifact_id
            for artifact_id, item in self._items.items()
            if now - item.created_at > ARTIFACT_TTL_SECONDS
        ]
        for artifact_id in stale:
            self._items.pop(artifact_id, None)
        total = sum(len(item.data) for item in self._items.values())
        while total > MAX_TOTAL_BYTES and self._items:
            oldest = min(self._items.values(), key=lambda item: item.created_at)
            total -= len(oldest.data)
            self._items.pop(oldest.artifact_id, None)

    def put(
        self,
        *,
        plugin_id: str,
        panel: str,
        filename: str,
        mime: str,
        data: bytes,
    ) -> ArtifactRecord:
        if not data:
            raise ValueError("EMPTY_ARTIFACT")
        if len(data) > MAX_ARTIFACT_BYTES:
            raise ValueError("ARTIFACT_TOO_LARGE")
        self._cleanup()
        record = ArtifactRecord(
            artifact_id=uuid.uuid4().hex,
            plugin_id=str(plugin_id or ""),
            panel=str(panel or ""),
            filename=str(filename or "artifact.bin")[:200],
            mime=str(mime or "application/octet-stream")[:120],
            data=bytes(data),
        )
        self._items[record.artifact_id] = record
        return record

    def get(self, artifact_id: str) -> ArtifactRecord | None:
        return self._items.get(str(artifact_id or ""))

    def snapshot(self, artifact_id: str) -> dict[str, Any] | None:
        item = self.get(artifact_id)
        if item is None:
            return None
        return {
            "artifact_id": item.artifact_id,
            "plugin_id": item.plugin_id,
            "panel": item.panel,
            "filename": item.filename,
            "mime": item.mime,
            "size": len(item.data),
            "created_at": item.created_at,
        }
