from __future__ import annotations

import asyncio
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from astrbot_plugin_update_manager.core.adapters.astrbot import AstrBotAdapter
from astrbot_plugin_update_manager.core.catalog import PluginCatalog


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
    core.sp = SimpleNamespace(global_get=global_get)
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


def star(name="demo", *, root_dir_name=None, reserved=False, activated=True):
    return SimpleNamespace(
        name=name,
        root_dir_name=root_dir_name or name,
        display_name=name,
        version="1.2.3",
        repo="https://github.com/acme/demo",
        reserved=reserved,
        activated=activated,
    )


def write_metadata(
    root, name="discovered", *, version="1.2.3", display_name=None
):
    plugin = root / name
    plugin.mkdir()
    display_name = display_name or f"{name} name"
    (plugin / "metadata.yaml").write_text(
        f"name: {name}\ndisplay_name: {display_name}\nversion: {version}\n"
        "repo: https://github.com/acme/discovered\n",
        encoding="utf-8",
    )
    return plugin


def test_adapter_runtime_dependencies_are_declared():
    requirements = Path(__file__).resolve().parents[1] / "requirements.txt"
    declared = {
        line.strip()
        for line in requirements.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    assert "PyYAML>=6.0" in declared


def test_probe_detects_contract(monkeypatch):
    install_shared_preferences(monkeypatch, {})
    report = AstrBotAdapter(FakeContext([star()], FakeManager())).probe_capabilities()
    assert report.plugin_manager and report.list_plugins and report.install_sources
    assert report.reload_plugin and report.update_plugin and report.cron_add_basic_job


def test_adapter_reads_real_astrbot_core_sp_layout(monkeypatch):
    install_shared_preferences(
        monkeypatch,
        {"demo": {"install_method": "github", "repo": "https://github.com/a/b"}},
    )
    # The real AstrBot 4.x singleton is astrbot.core.sp; the module itself only
    # defines SharedPreferences and has no module-level global_get function.
    del sys.modules["astrbot.core.utils.shared_preferences"].global_get
    adapter = AstrBotAdapter(FakeContext([star()]))

    snapshots = asyncio.run(adapter.snapshot_plugins())

    assert adapter.probe_capabilities().install_sources is True
    assert snapshots[0].install_source == {
        "install_method": "github",
        "repo": "https://github.com/a/b",
    }


def test_adapter_accepts_public_star_manager_alias():
    manager = FakeManager()
    adapter = AstrBotAdapter(SimpleNamespace(star_manager=manager, get_all_stars=lambda: []))
    assert adapter.plugin_manager is manager


def test_get_plugin_instance_reads_astrbot_4_star_cls():
    instance = SimpleNamespace(diagnostic_log_contract=lambda: {})
    metadata = star("astrbot_plugin_conversation_flow")
    metadata.star_cls = instance

    resolved = asyncio.run(
        AstrBotAdapter(FakeContext([metadata])).get_plugin_instance(
            "astrbot_plugin_conversation_flow"
        )
    )

    assert resolved is instance


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


def test_catalog_accepts_astrbot_427_repository_source(monkeypatch):
    install_shared_preferences(
        monkeypatch,
        {
            "demo": {
                "source": "repository",
                "url": "https://github.com/acme/demo",
            }
        },
    )
    adapter = AstrBotAdapter(FakeContext([star()]))

    item = asyncio.run(PluginCatalog(adapter).scan())[0]

    assert item.source_kind == "github"
    assert item.source_url == "https://github.com/acme/demo"
    assert "SOURCE_REQUIRED" not in item.reasons
    assert item.eligible


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
    # GitHub 仓库页不是归档下载地址，不能误传给 download_url。
    assert manager.updated == [("demo", "")]
    assert manager.reloaded == ["demo"]


def test_snapshot_merges_loaded_self_with_other_installed_plugins(monkeypatch, tmp_path):
    install_shared_preferences(monkeypatch, {})
    write_metadata(tmp_path, "astrbot_plugin_update_manager", version="9.9.9")
    write_metadata(tmp_path, "installed_only")
    manager = FakeManager()
    manager.plugin_store_path = tmp_path
    adapter = AstrBotAdapter(
        FakeContext([star("astrbot_plugin_update_manager")], manager)
    )
    snapshots = asyncio.run(adapter.snapshot_plugins())
    assert [item.name for item in snapshots] == [
        "astrbot_plugin_update_manager",
        "installed_only",
    ]
    assert snapshots[0].loaded is True
    assert snapshots[0].version == "1.2.3"
    assert snapshots[1].loaded is False
    assert snapshots[1].activated is False
    catalog = {item.plugin_id: item for item in asyncio.run(PluginCatalog(adapter).scan())}
    assert catalog["installed_only"].eligible is False
    assert "PLUGIN_NOT_LOADED" in catalog["installed_only"].reasons
    assert adapter.last_discovery_report.runtime_count == 1
    assert adapter.last_discovery_report.discovered_count == 1
    assert adapter.last_discovery_report.roots_checked == 1
    assert adapter.last_discovery_report.diagnostics == ()


def test_snapshot_deduplicates_by_root_before_plugin_id(monkeypatch, tmp_path):
    install_shared_preferences(monkeypatch, {})
    write_metadata(tmp_path, "runtime_root", version="9.9.9")
    write_metadata(tmp_path, "shared_id")
    manager = FakeManager()
    manager.plugin_store_path = tmp_path
    adapter = AstrBotAdapter(
        FakeContext([star("shared_id", root_dir_name="runtime_root")], manager)
    )
    snapshots = asyncio.run(adapter.snapshot_plugins())
    assert [(item.name, item.root_dir_name, item.loaded) for item in snapshots] == [
        ("shared_id", "runtime_root", True)
    ]
    assert snapshots[0].version == "1.2.3"
    assert adapter.last_discovery_report.discovered_count == 0


def test_snapshot_merge_preserves_runtime_id_and_prefers_metadata_display_name(
    monkeypatch, tmp_path
):
    install_shared_preferences(monkeypatch, {})
    write_metadata(
        tmp_path,
        "runtime_root",
        display_name="凝心溯溪-主动学习",
    )
    manager = FakeManager()
    manager.plugin_store_path = tmp_path
    runtime = star("active_learner", root_dir_name="runtime_root")
    runtime.display_name = "active_learner"

    snapshots = asyncio.run(AstrBotAdapter(FakeContext([runtime], manager)).snapshot_plugins())

    assert len(snapshots) == 1
    assert snapshots[0].name == "active_learner"
    assert snapshots[0].root_dir_name == "runtime_root"
    assert snapshots[0].display_name == "凝心溯溪-主动学习"
    catalog = asyncio.run(PluginCatalog(AstrBotAdapter(FakeContext([runtime], manager))).scan())
    assert catalog[0].plugin_id == "active_learner"
    assert catalog[0].display_name == "凝心溯溪-主动学习"


def test_snapshot_repairs_invalid_runtime_version_from_metadata(monkeypatch, tmp_path):
    install_shared_preferences(monkeypatch, {})
    write_metadata(tmp_path, "demo", version="1.2.4")
    manager = FakeManager()
    manager.plugin_store_path = tmp_path
    runtime = star("demo")
    runtime.version = "unknown (local checkout)"
    snapshots = asyncio.run(AstrBotAdapter(FakeContext([runtime], manager)).snapshot_plugins())
    assert len(snapshots) == 1
    assert snapshots[0].version == "1.2.4"
    assert snapshots[0].loaded is True
    assert snapshots[0].activated is True


def test_module_discovery_prefers_real_unicode_directory_path(monkeypatch, tmp_path):
    install_shared_preferences(monkeypatch, {})
    plugin = tmp_path / "凝心溯溪-声"
    plugin.mkdir()
    (plugin / "metadata.yaml").write_text(
        "name: astrbot_plugin_voice_hub\n"
        "display_name: 凝心溯溪-声\n"
        "version: 1.2.3\n",
        encoding="utf-8",
    )
    manager = FakeManager()
    manager.plugin_store_path = tmp_path
    manager._get_plugin_modules = lambda: {
        "astrbot_plugin_voice_hub": {
            "pname": "astrbot_plugin_voice_hub",
            "module_path": plugin / "main.py",
        }
    }
    snapshots = asyncio.run(AstrBotAdapter(FakeContext([], manager)).snapshot_plugins())
    assert len(snapshots) == 1
    assert snapshots[0].name == "astrbot_plugin_voice_hub"
    assert snapshots[0].display_name == "凝心溯溪-声"
    assert snapshots[0].root_dir_name == "凝心溯溪-声"


def test_snapshot_falls_back_to_installed_metadata_when_runtime_empty(
    monkeypatch, tmp_path
):
    install_shared_preferences(
        monkeypatch,
        {
            "unloaded": {
                "install_method": "github",
                "repo": "https://github.com/acme/discovered",
            }
        },
    )
    write_metadata(tmp_path, "unloaded")
    manager = FakeManager()
    manager.plugin_store_path = tmp_path
    adapter = AstrBotAdapter(FakeContext([], manager))
    snapshots = asyncio.run(adapter.snapshot_plugins())
    assert len(snapshots) == 1
    assert snapshots[0].name == "unloaded"
    assert snapshots[0].display_name == "unloaded name"
    assert snapshots[0].version == "1.2.3"
    assert snapshots[0].loaded is False
    assert snapshots[0].activated is False
    assert snapshots[0].install_source["install_method"] == "github"
    assert adapter.last_discovery_report.discovered_count == 1


def test_snapshot_fallback_supports_manager_modules_without_context_getter(
    monkeypatch, tmp_path
):
    install_shared_preferences(monkeypatch, {})
    plugin = write_metadata(tmp_path, "module_plugin")
    manager = FakeManager()
    manager.plugin_store_path = tmp_path
    manager._get_plugin_modules = lambda: {
        "module_plugin": {
            "pname": "module_plugin",
            "module": "main",
            "module_path": plugin / "main",
        }
    }
    context_without_getter = SimpleNamespace(_star_manager=manager)
    adapter = AstrBotAdapter(context_without_getter)
    snapshots = asyncio.run(adapter.snapshot_plugins())
    assert [item.name for item in snapshots] == ["module_plugin"]
    assert snapshots[0].loaded is False
    assert "RUNTIME_LIST_UNAVAILABLE" in adapter.last_discovery_report.diagnostics


def test_discovery_blocks_symlink_escape(monkeypatch, tmp_path):
    install_shared_preferences(monkeypatch, {})
    outside = tmp_path / "outside"
    outside.mkdir()
    write_metadata(outside, "escaped")
    root = tmp_path / "plugins"
    root.mkdir()
    try:
        (root / "escaped").symlink_to(outside / "escaped", target_is_directory=True)
    except OSError:
        pytest.skip("当前环境不允许创建目录符号链接")
    manager = FakeManager()
    manager.plugin_store_path = root
    adapter = AstrBotAdapter(FakeContext([], manager))
    assert asyncio.run(adapter.snapshot_plugins()) == ()
    assert "DISCOVERY_PATH_BLOCKED" in adapter.last_discovery_report.diagnostics


def test_update_rejects_discovered_but_unloaded_plugin(monkeypatch, tmp_path):
    install_shared_preferences(monkeypatch, {})
    write_metadata(tmp_path, "unloaded")
    manager = FakeManager()
    manager.plugin_store_path = tmp_path
    adapter = AstrBotAdapter(FakeContext([], manager))
    with pytest.raises(ValueError, match="MANAGEABLE"):
        asyncio.run(
            adapter.update_plugin(
                "unloaded",
                source_kind="github",
                source_url="https://github.com/acme/discovered",
            )
        )
    assert manager.updated == []


def test_update_passes_only_real_archive_to_download_url(monkeypatch):
    install_shared_preferences(monkeypatch, {})
    manager = FakeManager()
    adapter = AstrBotAdapter(FakeContext([star()], manager))
    asyncio.run(
        adapter.update_plugin(
            "demo",
            source_kind="github",
            source_url="https://github.com/acme/demo",
            archive_url="https://api.github.com/repos/acme/demo/zipball/v1.2.4",
        )
    )
    assert manager.updated == [
        ("demo", "https://api.github.com/repos/acme/demo/zipball/v1.2.4")
    ]


@pytest.mark.parametrize("archive_parameter", ["archive_url", "kwargs"])
def test_update_supports_archive_parameter_signature_variants(
    monkeypatch, archive_parameter
):
    install_shared_preferences(monkeypatch, {})

    class CompatibleManager(FakeManager):
        if archive_parameter == "archive_url":

            async def update_plugin(self, name, archive_url):
                self.updated.append((name, archive_url))

        else:

            async def update_plugin(self, name, **kwargs):
                self.updated.append((name, kwargs.get("download_url")))

    manager = CompatibleManager()
    adapter = AstrBotAdapter(FakeContext([star()], manager))
    archive_url = "https://api.github.com/repos/acme/demo/zipball/master"
    asyncio.run(
        adapter.update_plugin(
            "demo",
            source_kind="github",
            source_url="https://github.com/acme/demo",
            archive_url=archive_url,
        )
    )
    assert manager.updated == [("demo", archive_url)]


def test_install_enable_disable_use_416_contract_and_block_self(monkeypatch):
    install_shared_preferences(monkeypatch, {})
    ctx = FakeContext([])

    class LifecycleManager(FakeManager):
        async def install_plugin(self, repo_url, proxy=""):
            assert repo_url == "https://github.com/qsbb/astrbot_plugin_voice_hub"
            ctx._stars.append(star("astrbot_plugin_voice_hub", activated=True))
            return {"repo": repo_url}

        async def turn_off_plugin(self, plugin_name):
            next(item for item in ctx._stars if item.name == plugin_name).activated = False

        async def turn_on_plugin(self, plugin_name):
            next(item for item in ctx._stars if item.name == plugin_name).activated = True

    manager = LifecycleManager()
    ctx._star_manager = manager
    adapter = AstrBotAdapter(ctx)
    installed = asyncio.run(
        adapter.install_plugin(
            "astrbot_plugin_voice_hub",
            repo_url="https://github.com/qsbb/astrbot_plugin_voice_hub",
        )
    )
    assert installed.name == "astrbot_plugin_voice_hub"
    assert asyncio.run(
        adapter.set_plugin_enabled("astrbot_plugin_voice_hub", False)
    ).activated is False
    assert asyncio.run(
        adapter.set_plugin_enabled("astrbot_plugin_voice_hub", True)
    ).activated is True

    ctx._stars.append(star("astrbot_plugin_update_manager", activated=True))
    with pytest.raises(ValueError, match="SELF_DISABLE_BLOCKED"):
        asyncio.run(
            adapter.set_plugin_enabled("astrbot_plugin_update_manager", False)
        )
