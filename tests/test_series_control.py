from __future__ import annotations

import asyncio

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
