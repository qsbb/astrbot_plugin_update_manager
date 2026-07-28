from __future__ import annotations

import asyncio
from pathlib import Path
import sys
import types
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from astrbot_plugin_update_manager.core.diagnostics import SERIES_MEMBERS, diagnose_series


class _Adapter:
    def __init__(self):
        self.instances = {}

    async def snapshot_plugins(self):
        return tuple(
            types.SimpleNamespace(
                name=plugin_id,
                root_dir_name=plugin_id,
                version="1.0.0",
                loaded=True,
                activated=True,
            )
            for plugin_id, _label in SERIES_MEMBERS
        )

    async def get_plugin_instance(self, plugin_id):
        return self.instances.get(plugin_id)


class DiagnosticsTests(unittest.TestCase):
    def test_legacy_members_are_reported_as_compatible(self):
        report = asyncio.run(diagnose_series(_Adapter()))
        self.assertEqual(report["status"], "ok")
        self.assertEqual(report["healthy"], len(SERIES_MEMBERS))
        self.assertTrue(all(row["status"] == "compatible" for row in report["members"]))

    def test_declared_unhealthy_member_degrades_suite(self):
        adapter = _Adapter()
        plugin_id = SERIES_MEMBERS[0][0]
        adapter.instances[plugin_id] = types.SimpleNamespace(
            PLUGIN_HEALTH_CONTRACT="plugin.health@1.0",
            plugin_health=lambda: {
                "status": "unhealthy",
                "checks": {"storage_ready": False},
                "reasons": ["STORAGE_READY"],
                "version": "1.0.0",
            },
        )
        report = asyncio.run(diagnose_series(adapter))
        self.assertEqual(report["status"], "degraded")
        self.assertEqual(report["healthy"], len(SERIES_MEMBERS) - 1)


if __name__ == "__main__":
    unittest.main()
