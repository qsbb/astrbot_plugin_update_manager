from __future__ import annotations

import asyncio
import pathlib
import sys
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1].parent))

from astrbot_plugin_update_manager.core import backup_runner as br
from astrbot_plugin_update_manager.core.backup_runner import (
    BackupPaths,
    BackupRunner,
    OfficialBackupUnavailable,
    delete_backup,
    list_backups,
    validate_dir,
)


@pytest.fixture()
def paths(tmp_path):
    data = tmp_path / "data"
    plugins = data / "plugins"
    plugin_data = data / "plugin_data"
    backups = data / "backups"
    for item in (plugins, plugin_data, backups):
        item.mkdir(parents=True, exist_ok=True)
    return BackupPaths(
        data_dir=str(data),
        default_dir=str(backups),
        source_dirs=(str(plugins), str(plugin_data)),
    )


class FakeExporter:
    """记录调用的官方导出器替身。"""

    instances: list["FakeExporter"] = []

    def __init__(self, *, main_db, kb_manager, config_path) -> None:
        self.main_db = main_db
        self.kb_manager = kb_manager
        self.config_path = config_path
        self.calls: list[dict] = []
        FakeExporter.instances.append(self)

    async def export_all(self, *, output_dir, progress_callback=None):
        self.calls.append({"output_dir": output_dir, "has_progress": progress_callback is not None})
        if progress_callback is not None:
            await progress_callback("main_db", 1, 2, "导出主库")
            await progress_callback("directories", 2, 2, "导出目录")
        target = pathlib.Path(output_dir) / "astrbot_backup_20260922_033000.zip"
        target.write_bytes(b"zip-bytes")
        return str(target)


def _settings_paths(monkeypatch, paths):
    monkeypatch.setattr(br, "official_paths", lambda: paths)
    monkeypatch.setattr(br, "load_exporter", lambda: FakeExporter)
    FakeExporter.instances = []


# ------------------------------------------------------------------ 目录校验


def test_validate_dir_rejects_relative_path(paths):
    result = validate_dir("backups/local", paths=paths)
    assert result["ok"] is False
    assert result["error"] == br.ERROR_DIR_NOT_ABSOLUTE


def test_validate_dir_blank_falls_back_to_official_default(paths):
    result = validate_dir("", paths=paths)
    assert result["ok"] is True
    assert result["path"] == paths.default_dir


def test_validate_dir_rejects_directory_inside_backup_sources(paths, tmp_path):
    inside = pathlib.Path(paths.source_dirs[1]) / "backups"
    result = validate_dir(str(inside), paths=paths)
    assert result["ok"] is False
    assert result["error"] == br.ERROR_DIR_INSIDE_SOURCE


def test_validate_dir_rejects_unwritable_directory(paths, tmp_path, monkeypatch):
    target = tmp_path / "locked"
    target.mkdir()

    def boom(*args, **kwargs):
        raise OSError("read-only")

    monkeypatch.setattr(pathlib.Path, "write_text", boom)
    result = validate_dir(str(target), paths=paths)
    assert result["ok"] is False
    assert result["error"] == br.ERROR_DIR_NOT_WRITABLE


def test_validate_dir_rejects_illegal_characters(paths):
    """路径含非法字符时 Path.mkdir 抛 ValueError，也必须 fail-closed。"""
    result = validate_dir("/tmp/bad\x00name", paths=paths)
    assert result["ok"] is False
    assert result["error"] == br.ERROR_DIR_INVALID


def test_volume_root_walks_up_to_outermost_mount():
    """向上找到最外层挂载卷：非挂载路径最终落在 "/"，即容器文件系统。"""
    from astrbot_plugin_update_manager.core.backup_runner import volume_root

    def fake_ismount(path):
        return path in {"/", "/AstrBot/data"}

    assert str(volume_root(pathlib.Path("/mnt/nas/x/y"), ismount=fake_ismount)) == "/"
    assert str(volume_root(pathlib.Path("/AstrBot/data/backups"), ismount=fake_ismount)) == "/AstrBot/data"
    assert str(volume_root(pathlib.Path("/"), ismount=fake_ismount)) == "/"


def test_validate_dir_flags_container_layer_directory(paths, tmp_path, monkeypatch):
    """容器层目录（非挂载卷）必须标 ephemeral，供 UI 告警。"""
    monkeypatch.setattr(br, "volume_root", lambda p, **kw: pathlib.Path("/"))
    result = validate_dir(str(tmp_path / "container-layer"), paths=paths)
    assert result["ok"] is True
    assert result["ephemeral"] is True
    assert result["volume"] == "/"

    monkeypatch.setattr(br, "volume_root", lambda p, **kw: pathlib.Path(paths.data_dir))
    mounted = validate_dir("", paths=paths)
    assert mounted["ok"] is True
    assert mounted["ephemeral"] is False
    assert mounted["volume"] == paths.data_dir


def test_validate_dir_without_official_chain_is_fail_closed(monkeypatch):
    def missing():
        raise OfficialBackupUnavailable("no module")

    monkeypatch.setattr(br, "official_paths", missing)
    result = validate_dir("")
    assert result["ok"] is False
    assert result["error"] == br.ERROR_EXPORTER_UNAVAILABLE


# ------------------------------------------------------------------ 列表 / 删除


def test_list_and_delete_only_touch_official_backup_files(paths):
    target = pathlib.Path(paths.default_dir)
    (target / "astrbot_backup_20260920_030000.zip").write_bytes(b"a" * 10)
    (target / "astrbot_backup_20260921_030000.zip").write_bytes(b"b" * 20)
    (target / "other.zip").write_bytes(b"c" * 30)
    (target / "notes.txt").write_text("x", encoding="utf-8")

    listing = list_backups("", paths=paths)
    assert listing["success"] is True
    assert [item["name"] for item in listing["files"]] == [
        "astrbot_backup_20260921_030000.zip",
        "astrbot_backup_20260920_030000.zip",
    ]
    assert listing["total_bytes"] == 30

    removed = delete_backup("", "astrbot_backup_20260920_030000.zip", paths=paths)
    assert removed["success"] is True
    assert not (target / "astrbot_backup_20260920_030000.zip").exists()
    assert (target / "other.zip").exists()


def test_list_backups_flags_interrupted_files(paths):
    """官方导出器直接写最终文件名：被打断的截断文件必须标成不完整。"""
    import zipfile

    target = pathlib.Path(paths.default_dir)
    good = target / "astrbot_backup_20260922_033000.zip"
    with zipfile.ZipFile(good, "w") as archive:
        archive.writestr("manifest.json", "{}")
    broken = target / "astrbot_backup_20260921_033000.zip"
    broken.write_bytes(b"PK\x03\x04 truncated")

    listing = list_backups("", paths=paths)
    by_name = {item["name"]: item for item in listing["files"]}
    assert by_name["astrbot_backup_20260922_033000.zip"]["valid"] is True
    assert by_name["astrbot_backup_20260921_033000.zip"]["valid"] is False


def test_delete_backup_blocks_path_traversal_and_unknown_names(paths):
    target = pathlib.Path(paths.default_dir)
    (target / "astrbot_backup_keep.zip").write_bytes(b"k")
    for bad in ("../astrbot_backup_keep.zip", "/etc/passwd", "other.zip", ""):
        result = delete_backup("", bad, paths=paths)
        assert result["success"] is False
        assert result["error"] in {
            br.ERROR_DELETE_INVALID_NAME,
            br.ERROR_DELETE_NOT_FOUND,
        }
    assert (target / "astrbot_backup_keep.zip").exists()
    missing = delete_backup("", "astrbot_backup_missing.zip", paths=paths)
    assert missing["error"] == br.ERROR_DELETE_NOT_FOUND


# ------------------------------------------------------------------ runner


def _context(kb=True):
    db = SimpleNamespace(name="main-db")
    ctx = SimpleNamespace(get_db=lambda: db)
    if kb:
        ctx.kb_manager = SimpleNamespace(name="kb")
    return ctx


def test_runner_uses_official_exporter_and_reports_progress(monkeypatch, paths, tmp_path):
    _settings_paths(monkeypatch, paths)
    runner = BackupRunner(_context(), store=None)
    target = tmp_path / "external-backups"

    result = asyncio.run(runner.run(target_dir=str(target), trigger="manual"))

    assert result["success"] is True
    assert result["filename"] == "astrbot_backup_20260922_033000.zip"
    assert result["size_bytes"] == len(b"zip-bytes")
    assert result["kb_included"] is True
    exporter = FakeExporter.instances[-1]
    assert exporter.kb_manager is not None
    assert exporter.config_path == str(pathlib.Path(paths.data_dir) / "cmd_config.json")
    assert exporter.calls == [{"output_dir": str(target), "has_progress": True}]
    status = runner.status()
    assert status["running"] is False
    assert status["last_result"]["filename"] == result["filename"]


def test_runner_marks_missing_kb_manager_as_degraded(monkeypatch, paths, tmp_path):
    _settings_paths(monkeypatch, paths)
    runner = BackupRunner(_context(kb=False), store=None)
    result = asyncio.run(runner.run(target_dir=str(tmp_path / "b"), trigger="manual"))
    assert result["success"] is True
    assert result["kb_included"] is False


def test_runner_skips_when_already_running(monkeypatch, paths, tmp_path):
    _settings_paths(monkeypatch, paths)
    runner = BackupRunner(_context(), store=None)
    started = asyncio.Event()

    class SlowExporter(FakeExporter):
        async def export_all(self, *, output_dir, progress_callback=None):
            started.set()
            await asyncio.sleep(0.2)
            return await super().export_all(
                output_dir=output_dir, progress_callback=progress_callback
            )

    monkeypatch.setattr(br, "load_exporter", lambda: SlowExporter)

    async def scenario():
        first = asyncio.create_task(runner.run(target_dir=str(tmp_path / "b"), trigger="schedule"))
        await started.wait()
        second = await runner.run(target_dir=str(tmp_path / "b"), trigger="manual")
        return await first, second

    first, second = asyncio.run(scenario())
    assert first["success"] is True
    assert second["skipped"] is True
    assert second["error"] == br.ERROR_ALREADY_RUNNING
    assert len(SlowExporter.instances) == 1


def test_runner_fails_closed_and_surfaces_service_errors(monkeypatch, paths, tmp_path):
    _settings_paths(monkeypatch, paths)

    class BrokenExporter(FakeExporter):
        async def export_all(self, *, output_dir, progress_callback=None):
            raise RuntimeError("disk full api_key=sk-secret")

    monkeypatch.setattr(br, "load_exporter", lambda: BrokenExporter)
    runner = BackupRunner(_context(), store=None)
    result = asyncio.run(runner.run(target_dir=str(tmp_path / "b"), trigger="manual"))
    assert result["success"] is False
    assert result["error"] == br.ERROR_RUN_FAILED
    assert "sk-secret" not in result["detail"]
    assert "<已隐藏>" in result["detail"]

    def missing_exporter():
        raise OfficialBackupUnavailable("no backup module")

    monkeypatch.setattr(br, "load_exporter", missing_exporter)
    unavailable = asyncio.run(runner.run(target_dir=str(tmp_path / "b"), trigger="manual"))
    assert unavailable["success"] is False
    assert unavailable["error"] == br.ERROR_EXPORTER_UNAVAILABLE


def test_runner_rejects_bad_directory_before_calling_exporter(monkeypatch, paths):
    _settings_paths(monkeypatch, paths)
    runner = BackupRunner(_context(), store=None)
    result = asyncio.run(runner.run(target_dir="relative/path", trigger="manual"))
    assert result["success"] is False
    assert result["error"] == br.ERROR_DIR_NOT_ABSOLUTE
    assert FakeExporter.instances == []


def test_runner_survives_corrupt_state_file():
    """状态文件损坏不能让插件加载失败，也不能让状态查询抛异常。"""

    class BrokenStore:
        def read(self, key, default=None):
            raise ValueError("Expecting value: line 1 column 1 (char 0)")

        def write(self, key, value):
            raise OSError("disk full")

    runner = BackupRunner(_context(), store=BrokenStore())
    status = runner.status()
    assert status["success"] is True
    assert status["last_result"] is None
    assert status["running"] is False
    # 写入失败也不能抛（备份本身成功即可）
    runner._persist({"success": True})


def test_runner_emits_diagnostic_events(monkeypatch, paths, tmp_path):
    """备份必须留可观测足迹（成功路径），失败路径见下一个用例。"""
    from astrbot_plugin_update_manager.series_diagnostics import (
        diagnostic_clear,
        diagnostic_events,
    )

    _settings_paths(monkeypatch, paths)
    diagnostic_clear()
    runner = BackupRunner(_context(), store=None)
    asyncio.run(runner.run(target_dir=str(tmp_path / "b"), trigger="manual"))

    codes = [event["code"] for event in diagnostic_events(limit=50)["events"]]
    assert "backup.run.started" in codes
    assert "backup.run.completed" in codes

    # 失败时要有 failed 事件
    diagnostic_clear()

    class BrokenExporter(FakeExporter):
        async def export_all(self, *, output_dir, progress_callback=None):
            raise RuntimeError("boom")

    monkeypatch.setattr(br, "load_exporter", lambda: BrokenExporter)
    asyncio.run(runner.run(target_dir=str(tmp_path / "b"), trigger="schedule"))
    failed_codes = [event["code"] for event in diagnostic_events(limit=50)["events"]]
    assert "backup.run.failed" in failed_codes

    # 已在运行时跳过也要留痕
    diagnostic_clear()
    _settings_paths(monkeypatch, paths)
    running_runner = BackupRunner(_context(), store=None)
    running_runner._lock._locked = True  # 模拟有备份在跑
    try:
        skipped = asyncio.run(running_runner.run(target_dir=str(tmp_path / "b")))
        assert skipped["skipped"] is True
    finally:
        running_runner._lock._locked = False
    skipped_codes = [event["code"] for event in diagnostic_events(limit=50)["events"]]
    assert "backup.run.skipped" in skipped_codes


def test_runner_persists_last_result_to_store(monkeypatch, paths, tmp_path):
    _settings_paths(monkeypatch, paths)

    class Store:
        def __init__(self):
            self.data = {}

        def read(self, key, default=None):
            return self.data.get(key, default)

        def write(self, key, value):
            self.data[key] = value

    store = Store()
    runner = BackupRunner(_context(), store=store)
    asyncio.run(runner.run(target_dir=str(tmp_path / "b"), trigger="manual"))
    assert store.data["backup-state.json"]["last_result"]["success"] is True
    restored = BackupRunner(_context(), store=store)
    assert restored.status()["last_result"]["success"] is True


# ------------------------------------------------------------------ 调度


class FakeCron:
    def __init__(self) -> None:
        self.jobs: list[dict] = []
        self.deleted: list[str] = []

    def add_basic_job(self, *, name, cron_expression, handler, timezone):
        self.jobs.append(
            {"name": name, "cron": cron_expression, "handler": handler, "timezone": timezone}
        )
        return None

    def delete_job(self, name):
        self.deleted.append(name)


def test_backup_settings_read_from_config_and_validate():
    from astrbot_plugin_update_manager.core.backup_scheduler import (
        BackupScheduleError,
        BackupSettings,
        validate,
    )

    config = {
        "auto_backup_enabled": "true",
        "auto_backup_local_time": " 04:15 ",
        "auto_backup_timezone": "Asia/Shanghai",
    }
    settings = BackupSettings.from_config(lambda key, default=None: config.get(key, default))
    assert settings == BackupSettings(True, "04:15", "Asia/Shanghai")

    defaults = BackupSettings.from_config(lambda key, default=None: default)
    assert defaults.enabled is False
    assert defaults.local_time == "03:30"
    assert defaults.timezone == "Asia/Shanghai"

    for bad in (BackupSettings(True, "25:00", "Asia/Shanghai"), BackupSettings(True, "03:30", "Mars/Olympus")):
        with pytest.raises(BackupScheduleError) as excinfo:
            validate(bad)
        assert str(excinfo.value) == "INVALID_TIMEZONE_OR_TIME"


def test_backup_scheduler_registers_and_removes_job():
    from astrbot_plugin_update_manager.core.backup_scheduler import (
        JOB_ID,
        BackupScheduleService,
        BackupSettings,
    )

    cron = FakeCron()
    current = BackupSettings(True, "03:30", "Asia/Shanghai")
    handler_calls: list[BackupSettings] = []

    async def handler(settings):
        handler_calls.append(settings)

    service = BackupScheduleService(cron, lambda: current, handler)
    asyncio.run(service.rebuild())
    assert cron.deleted == [JOB_ID]
    assert cron.jobs == [
        {
            "name": JOB_ID,
            "cron": "30 3 * * *",
            "handler": service._runtime_handler,
            "timezone": "Asia/Shanghai",
        }
    ]
    assert service.ready is True
    assert service.last_error == ""

    # 关掉后不再注册
    current = BackupSettings(False, "03:30", "Asia/Shanghai")
    cron.jobs.clear()
    asyncio.run(service.rebuild())
    assert cron.jobs == []
    assert cron.deleted == [JOB_ID, JOB_ID]

    # close 也要清理任务
    asyncio.run(service.close())
    assert cron.deleted == [JOB_ID, JOB_ID, JOB_ID]


def test_backup_scheduler_reports_bad_config_and_missing_cron_without_raising():
    from astrbot_plugin_update_manager.core.backup_scheduler import (
        CRON_UNAVAILABLE,
        BackupScheduleService,
        BackupSettings,
    )

    cron = FakeCron()
    bad = BackupSettings(True, "99:99", "Asia/Shanghai")
    service = BackupScheduleService(cron, lambda: bad, lambda settings: None)
    asyncio.run(service.rebuild())  # 不抛：配置坏了也不能打断插件启动
    assert service.last_error == "INVALID_TIMEZONE_OR_TIME"
    assert cron.jobs == []

    good = BackupSettings(True, "03:30", "Asia/Shanghai")
    service = BackupScheduleService(None, lambda: good, lambda settings: None)
    asyncio.run(service.rebuild())
    assert service.last_error == CRON_UNAVAILABLE


def test_backup_scheduler_next_run_rolls_to_tomorrow():
    from astrbot_plugin_update_manager.core.backup_scheduler import (
        BackupScheduleService,
        BackupSettings,
    )

    service = BackupScheduleService(FakeCron(), lambda: BackupSettings(), lambda settings: None)
    enabled = BackupSettings(True, "03:30", "Asia/Shanghai")

    # 2026-09-21 17:00 UTC = 2026-09-22 01:00（上海）→ 当天 03:30 还没到
    before_run = datetime(2026, 9, 21, 17, 0, tzinfo=timezone.utc)
    upcoming = service.next_run(enabled, before_run)
    assert upcoming is not None
    assert upcoming.date().isoformat() == "2026-09-22"
    assert (upcoming.hour, upcoming.minute) == (3, 30)

    # 2026-09-22 01:00 UTC = 09:00（上海）→ 当天已过，顺延到次日
    after_run = datetime(2026, 9, 22, 1, 0, tzinfo=timezone.utc)
    rolled = service.next_run(enabled, after_run)
    assert rolled is not None
    assert rolled.date().isoformat() == "2026-09-23"

    assert service.next_run(BackupSettings(False, "03:30", "Asia/Shanghai"), after_run) is None


# ------------------------------------------------------------------ 定时触发链路


def test_backup_scheduler_runtime_handler_calls_handler_only_when_enabled():
    from astrbot_plugin_update_manager.core.backup_scheduler import (
        BackupScheduleService,
        BackupSettings,
    )

    cron = FakeCron()
    current = {"settings": BackupSettings(True, "03:30", "Asia/Shanghai")}
    seen: list[BackupSettings] = []

    async def handler(settings):
        seen.append(settings)

    service = BackupScheduleService(cron, lambda: current["settings"], handler)

    # 到点仍启用 → 调用
    asyncio.run(service._runtime_handler())
    assert [item.local_time for item in seen] == ["03:30"]

    # 到点前被关掉 → 不调用（避免用户关掉后仍偷偷备份）
    current["settings"] = BackupSettings(False, "03:30", "Asia/Shanghai")
    asyncio.run(service._runtime_handler())
    assert len(seen) == 1

    # 配置被改成非法值 → 也不调用，并记录 last_error
    current["settings"] = BackupSettings(True, "99:99", "Asia/Shanghai")
    asyncio.run(service._runtime_handler())
    assert len(seen) == 1
    assert service.last_error == "INVALID_TIMEZONE_OR_TIME"


def test_plugin_scheduled_backup_emits_diagnostics(monkeypatch, tmp_path):
    """cron 到点后：核必须真的跑一次备份，并把成功/跳过/失败都记进诊断。"""
    import sys

    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    from test_plugin_entry import context, import_main

    from astrbot_plugin_update_manager.core.backup_scheduler import BackupSettings
    from astrbot_plugin_update_manager.series_diagnostics import (
        diagnostic_clear,
        diagnostic_events,
    )

    module = import_main(monkeypatch)
    plugin = module.UpdateManagerPlugin(context(tmp_path), {})
    settings = BackupSettings(True, "03:30", "Asia/Shanghai")
    calls: list[str] = []

    async def ok_run(*, trigger="manual"):
        calls.append(trigger)
        return {"success": True, "filename": "astrbot_backup_x.zip", "size_bytes": 10}

    monkeypatch.setattr(plugin, "run_backup", ok_run)
    diagnostic_clear()
    asyncio.run(plugin._scheduled_backup(settings))
    codes = [event["code"] for event in diagnostic_events(limit=50)["events"]]
    assert calls == ["schedule"]
    assert "schedule.backup.started" in codes and "schedule.backup.completed" in codes

    async def skip_run(*, trigger="manual"):
        calls.append(trigger)
        return {"success": False, "skipped": True, "error": br.ERROR_ALREADY_RUNNING}

    monkeypatch.setattr(plugin, "run_backup", skip_run)
    diagnostic_clear()
    asyncio.run(plugin._scheduled_backup(settings))
    skipped = [event for event in diagnostic_events(limit=50)["events"] if event["code"] == "schedule.backup.completed"]
    assert skipped and skipped[-1]["level"] == "WARNING"

    async def fail_run(*, trigger="manual"):
        calls.append(trigger)
        return {"success": False, "error": br.ERROR_EXPORTER_UNAVAILABLE}

    monkeypatch.setattr(plugin, "run_backup", fail_run)
    diagnostic_clear()
    asyncio.run(plugin._scheduled_backup(settings))
    failed = [event for event in diagnostic_events(limit=50)["events"] if event["code"] == "schedule.backup.failed"]
    assert failed and failed[-1]["level"] == "ERROR"

    # run_backup 直接抛异常时：诊断要收尾、且异常绝不能抛回 cron
    async def boom_run(*, trigger="manual"):
        raise RuntimeError("unexpected explosion")

    monkeypatch.setattr(plugin, "run_backup", boom_run)
    diagnostic_clear()
    asyncio.run(plugin._scheduled_backup(settings))  # 不抛
    events = diagnostic_events(limit=50)["events"]
    failed_events = [event for event in events if event["code"] == "schedule.backup.failed"]
    assert failed_events, [event["code"] for event in events]
    assert failed_events[-1]["details"].get("reason") == "SCHEDULED_BACKUP_FAILED"
