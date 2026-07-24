from __future__ import annotations

import asyncio
import importlib
import sys
import types
from pathlib import Path
from types import SimpleNamespace

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT.parent))


class Logger:
    def __getattr__(self, name):
        return lambda *args, **kwargs: None


class CommandGroupDecorator:
    def __call__(self, func):
        func.command = lambda _name: lambda child: child
        return func


def passthrough_decorator(*args, **kwargs):
    return lambda func: func


def install_astrbot_api_stubs(monkeypatch):
    astrbot = types.ModuleType("astrbot")
    api = types.ModuleType("astrbot.api")
    event = types.ModuleType("astrbot.api.event")
    star = types.ModuleType("astrbot.api.star")

    class Star:
        def __init__(self, context):
            self.context = context

    event.AstrMessageEvent = object
    event.filter = SimpleNamespace(
        PermissionType=SimpleNamespace(ADMIN="admin"),
        permission_type=passthrough_decorator,
        command_group=lambda _name: CommandGroupDecorator(),
    )
    star.Context = object
    star.Star = Star
    star.register = passthrough_decorator
    api.logger = Logger()
    api.event = event
    api.star = star
    astrbot.api = api
    for name, module in {
        "astrbot": astrbot,
        "astrbot.api": api,
        "astrbot.api.event": event,
        "astrbot.api.star": star,
    }.items():
        monkeypatch.setitem(sys.modules, name, module)


def import_main(monkeypatch):
    install_astrbot_api_stubs(monkeypatch)
    sys.modules.pop("astrbot_plugin_auto_updater.main", None)
    return importlib.import_module("astrbot_plugin_auto_updater.main")


def context(tmp_path):
    return SimpleNamespace(
        get_all_stars=lambda: [],
        cron_manager=None,
        version="4.26.4",
        get_plugin_data_dir=lambda name: tmp_path / name,
    )


def test_entry_identity_defaults_and_data_location(monkeypatch, tmp_path):
    module = import_main(monkeypatch)
    plugin = module.AutoUpdaterPlugin(context(tmp_path), {})
    assert module.PLUGIN_NAME == "astrbot_plugin_auto_updater"
    assert module.__version__ == "0.4.0"
    assert plugin.enabled is True and plugin.auto_update_enabled is False
    assert plugin.store.root == (tmp_path / module.PLUGIN_NAME).resolve()


def test_input_validation_and_rule_default_off(monkeypatch, tmp_path):
    module = import_main(monkeypatch)
    plugin = module.AutoUpdaterPlugin(context(tmp_path), {})
    assert plugin._parse_ids("a,b,a") == ("a", "b")
    for value in ("", "../x", "a/b"):
        try:
            plugin._parse_ids(value)
            assert False
        except ValueError:
            pass
    assert plugin.scheduler.load().enabled is False


def test_commands_and_terminate_cleanup(monkeypatch, tmp_path):
    module = import_main(monkeypatch)
    plugin = module.AutoUpdaterPlugin(context(tmp_path), {})
    event = SimpleNamespace(plain_result=lambda text: text)

    async def collect(generator):
        return [item async for item in generator]

    probe = asyncio.run(collect(plugin.aup_probe(event)))[0]
    catalog = asyncio.run(collect(plugin.aup_catalog(event)))[0]
    cancel = asyncio.run(collect(plugin.aup_cancel(event)))[0]
    assert "能力探针" in probe and "插件目录（0 项）" in catalog
    assert "事务边界" in cancel
    asyncio.run(plugin.initialize())
    asyncio.run(plugin.terminate())
    assert (
        plugin._terminated
        and plugin.adapter is None
        and module._current_instance is None
    )
