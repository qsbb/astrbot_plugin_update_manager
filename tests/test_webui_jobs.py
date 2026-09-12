from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1].parent))

from astrbot_plugin_update_manager.core.webui_jobs import JobManager


def test_job_manager_lifecycle():
    jobs = JobManager()
    job = jobs.create(plugin_id="astrbot_plugin_active_learner", panel="memories", action="import")
    assert job.status == "running"

    jobs.update(job.job_id, progress=0.5, message="half")
    snapshot = jobs.snapshot(job.job_id)
    assert snapshot["progress"] == 0.5
    assert snapshot["message"] == "half"

    jobs.cancel(job.job_id)
    assert jobs.snapshot(job.job_id)["status"] == "cancelling"

    jobs.update(job.job_id, status="done", progress=1.0, result={"ok": True})
    done = jobs.snapshot(job.job_id)
    assert done["status"] == "done"
    assert done["result"] == {"ok": True}
    assert jobs.list_for_plugin("astrbot_plugin_active_learner")
