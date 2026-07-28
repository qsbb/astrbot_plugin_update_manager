from __future__ import annotations

import asyncio
from pathlib import Path
import sys
import types
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from astrbot_plugin_update_manager.core.health import HealthChecker


class _Adapter:
    def __init__(self, instance):
        self.instance = instance

    async def get_plugin(self, plugin_id):
        return types.SimpleNamespace(version="1.2.3", activated=True)

    async def get_plugin_instance(self, plugin_id):
        return self.instance


class HealthContractTests(unittest.TestCase):
    def test_legacy_plugin_without_contract_keeps_l0_compatibility(self):
        result = asyncio.run(
            HealthChecker(_Adapter(object())).check(
                "demo", "1.2.3", expected_activated=True
            )
        )
        self.assertTrue(result.healthy)

    def test_declared_business_failure_is_unhealthy(self):
        instance = types.SimpleNamespace(
            PLUGIN_HEALTH_CONTRACT="plugin.health@1.0",
            plugin_health=lambda: {
                "status": "degraded",
                "checks": {"storage_ready": False},
                "reasons": ["STORAGE_READY"],
                "version": "1.2.3",
            },
        )
        result = asyncio.run(
            HealthChecker(_Adapter(instance)).check(
                "demo", "1.2.3", expected_activated=True
            )
        )
        self.assertFalse(result.healthy)
        self.assertEqual(result.reason, "BUSINESS_HEALTH_UNHEALTHY")

    def test_malformed_declared_contract_fails_closed(self):
        instance = types.SimpleNamespace(
            PLUGIN_HEALTH_CONTRACT="plugin.health@1.0",
            plugin_health=lambda: {"status": "ok"},
        )
        result = asyncio.run(
            HealthChecker(_Adapter(instance)).check(
                "demo", "1.2.3", expected_activated=True
            )
        )
        self.assertFalse(result.healthy)
        self.assertEqual(result.reason, "HEALTH_CONTRACT_INVALID")


if __name__ == "__main__":
    unittest.main()
