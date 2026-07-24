from __future__ import annotations

import asyncio
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from astrbot_plugin_update_manager.core.adapters.astrbot import AstrBotAdapter


class FakeManager:
    def __init__(self):
        self.updated = []
        self.reloaded = []

    async def reload(self, name=None):
        self.reloaded.append(name)
        return True, None

    async def update_plugin(self, name, proxy="", download_url=""):
        self.updated.append((name, download_url))


class FakeCron:
    def add_basic_job(self, *args, **kwargs):
        return None


class FakeContext:
    def __init__(self, stars=(), manager=None):
        self._stars = list(stars)
        self._star_manager = manager
        self.cron_manager = FakeCron()

    def get_all_stars(self):
        return list(self._stars)


def install_shared_preferences(monkeypatch, records):
    astrbot = types.ModuleType("astrbot")
    core = types.ModuleType("astrbot.core")
    utils = types.ModuleType("astrbot.core.utils")
    shared = types.ModuleType("astrbot.core.utils.shared_preferences")

    async def global_get(key, default):
        return records

    shared.global_get = global_get
    utils.shared_preferences = shared
    core.utils = utils
    astrbot.core = core
    for name, module in {
        "astrbot": astrbot,
        "astrbot.core": core,
        "astrbot.core.utils": utils,
        "astrbot.core.utils.shared_preferences": shared,
    }.items():
        monkeypatch.setitem(sys.modules, name, module)


def star(name="demo", *, reserved=False, activated=True):
    return SimpleNamespace(
        name=name,
        root_dir_name=name,
        display_name=name,
        version="1.2.3",
        repo="https://github.com/acme/demo",
        reserved=reserved,
        activated=activated,
    )


def test_probe_detects_contract(monkeypatch):
    install_shared_preferences(monkeypatch, {})
    report = AstrBotAdapter(FakeContext([star()], FakeManager())).probe_capabilities()
    assert report.plugin_manager and report.list_plugins and report.install_sources
    assert report.reload_plugin and report.update_plugin and report.cron_add_basic_job


def test_snapshot_preserves_source_reserved_and_disabled(monkeypatch):
    install_shared_preferences(
        monkeypatch,
        {"demo": {"install_method": "github", "repo": "https://github.com/acme/demo"}},
    )
    snapshots = asyncio.run(
        AstrBotAdapter(FakeContext([star(activated=False)])).snapshot_plugins()
    )
    assert snapshots[0].install_source["install_method"] == "github"
    assert snapshots[0].activated is False


def test_mutation_rejects_self_reserved_and_unknown_source(monkeypatch):
    install_shared_preferences(monkeypatch, {})
    adapter = AstrBotAdapter(
        FakeContext([star(), star("reserved", reserved=True)], FakeManager())
    )
    with pytest.raises(ValueError, match="SELF_UPDATE"):
        asyncio.run(
            adapter.update_plugin(
                "astrbot_plugin_update_manager",
                source_kind="github",
                source_url="https://github.com/a/b",
            )
        )
    with pytest.raises(ValueError, match="SOURCE_REQUIRED"):
        asyncio.run(adapter.update_plugin("demo", source_kind="upload", source_url="x"))
    with pytest.raises(ValueError, match="MANAGEABLE"):
        asyncio.run(
            adapter.update_plugin(
                "reserved", source_kind="github", source_url="https://github.com/a/b"
            )
        )


def test_update_and_reload_use_core_manager(monkeypatch):
    install_shared_preferences(monkeypatch, {})
    manager = FakeManager()
    adapter = AstrBotAdapter(FakeContext([star()], manager))
    asyncio.run(
        adapter.update_plugin(
            "demo", source_kind="github", source_url="https://github.com/acme/demo"
        )
    )
    asyncio.run(adapter.reload_plugin("demo"))
    assert manager.updated == [("demo", "https://github.com/acme/demo")]
    assert manager.reloaded == ["demo"]
