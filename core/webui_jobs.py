"""series.webui@2.0 长任务 job 的内存管理。

job 由插件面板动作创建；核只保存进度/状态/取消标记，不保存插件业务状态。
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

MAX_JOBS = 200
JOB_TTL_SECONDS = 30 * 60


@dataclass
class JobRecord:
    job_id: str
    plugin_id: str
    panel: str
    action: str
    status: str = "running"
    progress: float = 0.0
    message: str = ""
    result: dict[str, Any] | None = None
    error: str = ""
    cancel_requested: bool = False
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def snapshot(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "plugin_id": self.plugin_id,
            "panel": self.panel,
            "action": self.action,
            "status": self.status,
            "progress": max(0.0, min(1.0, float(self.progress))),
            "message": self.message,
            "result": self.result,
            "error": self.error,
            "cancel_requested": self.cancel_requested,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class JobManager:
    def __init__(self, *, max_jobs: int = MAX_JOBS) -> None:
        self._jobs: dict[str, JobRecord] = {}
        self._max_jobs = max(1, int(max_jobs))

    def _cleanup(self) -> None:
        now = time.time()
        stale = [
            job_id
            for job_id, job in self._jobs.items()
            if now - job.updated_at > JOB_TTL_SECONDS
        ]
        for job_id in stale:
            self._jobs.pop(job_id, None)
        while len(self._jobs) > self._max_jobs:
            oldest = min(self._jobs.values(), key=lambda item: item.updated_at)
            self._jobs.pop(oldest.job_id, None)

    def create(self, *, plugin_id: str, panel: str, action: str) -> JobRecord:
        self._cleanup()
        job = JobRecord(
            job_id=uuid.uuid4().hex,
            plugin_id=str(plugin_id or ""),
            panel=str(panel or ""),
            action=str(action or ""),
        )
        self._jobs[job.job_id] = job
        return job

    def get(self, job_id: str) -> JobRecord | None:
        return self._jobs.get(str(job_id or ""))

    def update(
        self,
        job_id: str,
        *,
        status: str | None = None,
        progress: float | None = None,
        message: str | None = None,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> JobRecord | None:
        job = self.get(job_id)
        if job is None:
            return None
        if status is not None:
            job.status = str(status)
        if progress is not None:
            job.progress = max(0.0, min(1.0, float(progress)))
        if message is not None:
            job.message = str(message)
        if result is not None:
            job.result = dict(result)
        if error is not None:
            job.error = str(error)
        job.updated_at = time.time()
        return job

    def cancel(self, job_id: str) -> JobRecord | None:
        job = self.get(job_id)
        if job is None:
            return None
        if job.status in {"done", "failed", "cancelled"}:
            return job
        job.cancel_requested = True
        job.status = "cancelling"
        job.message = job.message or "取消请求已发送"
        job.updated_at = time.time()
        return job

    def snapshot(self, job_id: str) -> dict[str, Any] | None:
        job = self.get(job_id)
        return job.snapshot() if job is not None else None

    def list_for_plugin(self, plugin_id: str) -> list[dict[str, Any]]:
        return [
            job.snapshot()
            for job in self._jobs.values()
            if job.plugin_id == str(plugin_id or "")
        ]
