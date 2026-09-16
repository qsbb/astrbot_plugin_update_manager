from __future__ import annotations

import asyncio
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1].parent))

from astrbot_plugin_update_manager.core.adapters.storage import AtomicJsonStore
from astrbot_plugin_update_manager.core.series_control import SeriesControlGateway


class FakePlugin:
    def series_control_contract(self):
        return {"name": "series.control@1.0", "version": "1.0", "series_id": "ningxin_suxi", "plugin_id": "astrbot_plugin_active_learner"}

    def series_control_schema(self):
        return {"fields": {"enabled": {"type": "bool", "default": True}}}

    def series_control_snapshot(self):
        return {"fields": {"enabled": {"effective_value": True, "effective_source": "plugin"}}}

    def validate_series_control_patch(self, patch, *, expected_revision):
        return {"valid": isinstance(patch.get("enabled"), bool)}

    def apply_series_control_patch(self, patch, *, expected_revision):
        return {"success": True}


class FakeAdapter:
    async def get_plugin_instance(self, plugin_id):
        return FakePlugin() if plugin_id == "astrbot_plugin_active_learner" else None


def test_control_native_and_revision(tmp_path):
    gateway = SeriesControlGateway(FakeAdapter(), AtomicJsonStore(tmp_path))
    async def run():
        assert (await gateway.schema("astrbot_plugin_active_learner"))["success"]
        assert gateway.mode == "native"
        try:
            await gateway.apply("astrbot_plugin_active_learner", {"enabled": False}, 0, "admin")
        except PermissionError as exc:
            assert str(exc) == "TAKEOVER_DISABLED"
        else:
            raise AssertionError("native mode must not apply overrides")
        await gateway.set_mode("managed", "owner")
        result = await gateway.apply("astrbot_plugin_active_learner", {"enabled": False}, 0, "admin")
        assert result["revision"] == 1
        try:
            await gateway.apply("astrbot_plugin_active_learner", {"enabled": True}, 0, "admin")
        except ValueError as exc:
            assert str(exc) == "REVISION_CONFLICT"
        else:
            raise AssertionError("revision conflict was not raised")
    asyncio.run(run())


def test_unknown_plugin_fails_closed(tmp_path):
    gateway = SeriesControlGateway(FakeAdapter(), AtomicJsonStore(tmp_path))
    async def run():
        try:
            await gateway.schema("third_party_plugin")
        except LookupError as exc:
            assert str(exc) == "PLUGIN_NOT_TRUSTED"
        else:
            raise AssertionError("third-party plugin was accepted")
    asyncio.run(run())


class FakePluginNative(FakePlugin):
    """支持一键固化/读取原生值的最小桩。"""

    def __init__(self):
        self.config = {"enabled": False}
        self.calls = []

    def series_control_schema(self):
        return {"fields": {"enabled": {"type": "bool", "default": True, "control": "overrideable", "secret": False}}}

    def series_control_snapshot(self):
        return {"fields": {"enabled": {"native_configured": True, "managed_configured": True,
                                       "effective_source": "managed", "effective_value": True,
                                       "native_value": False}}}

    def series_control_native_write(self, patch, *, expected_revision=None):
        self.calls.append(("write_native", dict(patch)))
        self.config.update(patch)
        return {"status": "ok", "reason": "APPLIED", "written": list(patch), "skipped": [], "backup_id": "20260916-120000"}

    def reset_series_control_override(self, fields=None, *, expected_revision=None):
        self.calls.append(("reset", list(fields or [])))
        return {"status": "ok"}


class FakeAdapterNative:
    def __init__(self, plugin):
        self.plugin = plugin

    async def get_plugin_instance(self, plugin_id):
        return self.plugin if plugin_id == "astrbot_plugin_active_learner" else None


def test_freeze_writes_native_and_clears_overlay(tmp_path):
    plugin = FakePluginNative()
    gateway = SeriesControlGateway(FakeAdapterNative(plugin), AtomicJsonStore(tmp_path))

    async def run():
        await gateway.set_mode("managed", "owner")
        member = gateway._member("astrbot_plugin_active_learner")
        member["overrides"]["enabled"] = True
        member["revision"] = 1
        result = await gateway.freeze("astrbot_plugin_active_learner", reset_overlay=True, role="owner")
        assert result["status"] == "frozen"
        assert result["written"] == ["enabled"]
        assert result["backup_id"] == "20260916-120000"
        assert plugin.config["enabled"] is True
        assert ("write_native", {"enabled": True}) in plugin.calls
        assert not gateway._member("astrbot_plugin_active_learner")["overrides"]

    asyncio.run(run())


def test_native_snapshot_and_import_native_expose_native_values(tmp_path):
    plugin = FakePluginNative()
    gateway = SeriesControlGateway(FakeAdapterNative(plugin), AtomicJsonStore(tmp_path))

    async def run():
        await gateway.set_mode("managed", "owner")
        native = await gateway.native_snapshot("astrbot_plugin_active_learner")
        assert native["supported"] is True
        assert native["fields"]["enabled"]["native_value"] is False

    asyncio.run(run())


class FakePluginModeBroken(FakePlugin):
    """模拟线上 序(identity_guardian) 0.8.5 的缺陷：set_mode 转发到不存在的方法。"""

    def series_control_set_mode(self, mode):
        raise AttributeError("'SeriesControlAdapter' object has no attribute 'set_mode'")


class FakeAdapterModeBroken:
    async def get_plugin_instance(self, plugin_id):
        return FakePluginModeBroken() if plugin_id == "astrbot_plugin_active_learner" else None


def test_plugin_mode_sync_failure_does_not_break_reads(tmp_path):
    """插件侧模式同步失败时，schema/snapshot 仍要可用，并把原因回报给前端。"""
    gateway = SeriesControlGateway(FakeAdapterModeBroken(), AtomicJsonStore(tmp_path))

    async def run():
        schema = await gateway.schema("astrbot_plugin_active_learner")
        snapshot = await gateway.snapshot("astrbot_plugin_active_learner")
        assert schema["success"] and snapshot["success"]
        assert "set_mode" in schema["mode_error"] and "set_mode" in snapshot["mode_error"]
        overview = await gateway.overview()
        row = next(
            item
            for item in overview["members"]
            if item["plugin_id"] == "astrbot_plugin_active_learner"
        )
        assert row["reason"] == "MODE_SYNC_FAILED"
        assert "set_mode" in row["mode_error"]

    asyncio.run(run())
